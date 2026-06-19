import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ActionIcon,
  Accordion,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  TextInput,
  NumberInput,
  Title,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { api } from "../api";
import { useAuth } from "../auth";
import { computeEndDate, copyRich, copyText, notifyErr, notifyOk } from "../lib";
import { FieldInput } from "../components/SetupFields";
import { Gantt, MonthGrid } from "../components/Calendar";
import type { Experiment, ExpType, FieldDef, Protocol, Report, Task } from "../types";

const NEW_TYPE = "__new__";

function useProtocols() {
  return useQuery<Protocol[]>({ queryKey: ["protocols"], queryFn: () => api.get("/protocols") });
}

// ── Browse ────────────────────────────────────────────────────────────────────
function ExperimentRow({ exp, onEdit }: { exp: Experiment; onEdit: (id: number) => void }) {
  const qc = useQueryClient();
  const { data: report } = useQuery<Report>({
    queryKey: ["report", exp.id],
    queryFn: () => api.get(`/experiments/${exp.id}/report`),
  });
  const { data: tasks } = useQuery<Task[]>({
    queryKey: ["tasks", exp.id],
    queryFn: () => api.get(`/experiments/${exp.id}/tasks`),
  });
  const del = useMutation({
    mutationFn: () => api.del(`/experiments/${exp.id}`),
    onSuccess: () => {
      notifyOk("Experiment deleted.");
      qc.invalidateQueries({ queryKey: ["experiments"] });
    },
    onError: notifyErr,
  });

  const sched =
    exp.start_date && exp.end_date && exp.end_date !== exp.start_date
      ? `${exp.start_date} → ${exp.end_date}`
      : exp.start_date || "";

  return (
    <Stack>
      {sched && (
        <Text size="sm" c="dimmed">
          🗓 {sched}
        </Text>
      )}
      {report && <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontFamily: "inherit" }}>{report.markdown}</pre>}

      {tasks && tasks.length > 0 && (
        <div>
          <Text fw={600} size="sm">
            Tasks ({tasks.filter((t) => t.status === "done").length}/{tasks.length} done)
          </Text>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>✓</Table.Th>
                <Table.Th>Task</Table.Th>
                <Table.Th>Date</Table.Th>
                <Table.Th>Sample</Table.Th>
                <Table.Th>Reagent</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {tasks.map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td>{t.status === "done" ? "✅" : "⬜"}</Table.Td>
                  <Table.Td>{t.task_name}</Table.Td>
                  <Table.Td>{t.planned_date}</Table.Td>
                  <Table.Td>{t.sample}</Table.Td>
                  <Table.Td>{t.reagent}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      )}

      <Group>
        <Button
          size="xs"
          variant="light"
          onClick={() => report && copyRich(report.html, report.text)}
        >
          📋 Copy for Labguru (rich)
        </Button>
        <Button size="xs" variant="default" onClick={() => report && copyText(report.text)}>
          Copy plain text
        </Button>
        <Button size="xs" onClick={() => onEdit(exp.id)}>
          ✏️ Edit
        </Button>
        <Button size="xs" color="red" variant="light" onClick={() => del.mutate()}>
          🗑 Delete
        </Button>
      </Group>
    </Stack>
  );
}

function BrowseTab({
  experiments,
  onEdit,
}: {
  experiments: Experiment[];
  onEdit: (id: number) => void;
}) {
  if (experiments.length === 0)
    return (
      <Text c="dimmed" size="sm">
        No experiments yet. Create one in <b>Create / Edit</b>, or import an Excel
        plan from <b>Import</b>.
      </Text>
    );
  return (
    <Accordion variant="separated">
      {experiments.map((e) => (
        <Accordion.Item key={e.id} value={String(e.id)}>
          <Accordion.Control>
            🧬 {e.name}
            {e.type_name ? ` · ${e.type_name}` : ""} ·{" "}
            <Badge size="sm" variant="light" ml={4}>
              {e.status}
            </Badge>
          </Accordion.Control>
          <Accordion.Panel>
            <ExperimentRow exp={e} onEdit={onEdit} />
          </Accordion.Panel>
        </Accordion.Item>
      ))}
    </Accordion>
  );
}

// ── Tasks editor (within Create/Edit) ────────────────────────────────────────
function TasksEditor({ experimentId }: { experimentId: number }) {
  const qc = useQueryClient();
  const { data: tasks } = useQuery<Task[]>({
    queryKey: ["tasks", experimentId],
    queryFn: () => api.get(`/experiments/${experimentId}/tasks`),
  });
  const [name, setName] = useState("");
  const [date, setDate] = useState<Date | null>(null);
  const invalidate = () => qc.invalidateQueries({ queryKey: ["tasks", experimentId] });

  const toggle = useMutation({
    mutationFn: (t: Task) =>
      api.put(`/experiments/tasks/${t.id}/status`, {
        status: t.status === "done" ? "pending" : "done",
      }),
    onSuccess: invalidate,
    onError: notifyErr,
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.del(`/experiments/tasks/${id}`),
    onSuccess: invalidate,
    onError: notifyErr,
  });
  const add = useMutation({
    mutationFn: () =>
      api.post(`/experiments/${experimentId}/tasks`, {
        task_name: name,
        planned_date: date ? date.toISOString().slice(0, 10) : null,
      }),
    onSuccess: () => {
      setName("");
      setDate(null);
      invalidate();
    },
    onError: notifyErr,
  });

  return (
    <Stack gap="xs">
      <Text fw={600}>Tasks / milestones</Text>
      {(tasks ?? []).map((t) => (
        <Group key={t.id} justify="space-between" wrap="nowrap">
          <Text size="sm" td={t.status === "done" ? "line-through" : undefined}>
            {t.task_name} {t.planned_date ? `· ${t.planned_date}` : ""}
          </Text>
          <Group gap={4}>
            <ActionIcon variant="subtle" onClick={() => toggle.mutate(t)}>
              {t.status === "done" ? "↩︎" : "✅"}
            </ActionIcon>
            <ActionIcon variant="subtle" color="red" onClick={() => remove.mutate(t.id)}>
              🗑
            </ActionIcon>
          </Group>
        </Group>
      ))}
      <Group align="end">
        <TextInput
          placeholder="New task…"
          value={name}
          onChange={(e) => setName(e.currentTarget.value)}
          style={{ flex: 1 }}
        />
        <DateInput placeholder="Date" value={date} onChange={setDate} valueFormat="YYYY-MM-DD" clearable />
        <Button onClick={() => add.mutate()} disabled={!name.trim()}>
          ➕ Add task
        </Button>
      </Group>
    </Stack>
  );
}

// ── Create / Edit form ────────────────────────────────────────────────────────
function EditForm({
  experiment,
  types,
  protocols,
  onSaved,
}: {
  experiment: Experiment | null;
  types: ExpType[];
  protocols: Protocol[];
  onSaved: () => void;
}) {
  const { meta } = useAuth();
  const qc = useQueryClient();

  const [typeId, setTypeId] = useState<number | null>(
    experiment?.type_id ?? (types[0]?.id ?? null),
  );
  const [name, setName] = useState(experiment?.name ?? "");
  const [setup, setSetup] = useState<Record<string, unknown>>(experiment?.setup ?? {});
  const [startDate, setStartDate] = useState<Date | null>(
    experiment?.start_date ? new Date(experiment.start_date + "T00:00:00") : new Date(),
  );
  const [duration, setDuration] = useState<number>(experiment?.duration_days ?? 1);
  const [status, setStatus] = useState<string>(experiment?.status ?? "planned");
  const [description, setDescription] = useState(experiment?.description ?? "");
  const [newTypeName, setNewTypeName] = useState("");

  const selectedType = types.find((t) => t.id === typeId) ?? null;
  const fields: FieldDef[] = selectedType?.fields ?? [];
  const startStr = startDate ? startDate.toISOString().slice(0, 10) : null;
  const endPreview = computeEndDate(startStr, duration);

  const createType = useMutation({
    mutationFn: () => api.post("/types", { name: newTypeName.trim() }),
    onSuccess: async (r) => {
      setNewTypeName("");
      await qc.invalidateQueries({ queryKey: ["types"] });
      setTypeId(r.id);
      notifyOk("Type created. Customize its fields under Types & Lists.");
    },
    onError: notifyErr,
  });

  const save = useMutation({
    mutationFn: () => {
      const protoField = fields.find((f) => f.kind === "protocol" && setup[f.key]);
      const payload = {
        name,
        type_id: typeId,
        start_date: startStr,
        duration_days: duration,
        protocol_id: protoField ? (setup[protoField.key] as number) : null,
        setup_values: setup,
        description: description || null,
        status,
      };
      return experiment
        ? api.put(`/experiments/${experiment.id}`, payload)
        : api.post("/experiments", payload);
    },
    onSuccess: () => {
      notifyOk(experiment ? `Updated '${name}'.` : `Created '${name}'.`);
      qc.invalidateQueries({ queryKey: ["experiments"] });
      onSaved();
    },
    onError: notifyErr,
  });

  return (
    <Stack>
      <Group align="end">
        <Select
          label="Experiment type"
          data={[
            ...types.map((t) => ({ value: String(t.id), label: t.name })),
            { value: NEW_TYPE, label: "➕ Add new type…" },
          ]}
          value={typeId ? String(typeId) : NEW_TYPE}
          onChange={(v) => setTypeId(v && v !== NEW_TYPE ? Number(v) : null)}
          allowDeselect={false}
          w={300}
        />
      </Group>

      {typeId === null && (
        <Group align="end">
          <TextInput
            label="New type name"
            value={newTypeName}
            onChange={(e) => setNewTypeName(e.currentTarget.value)}
            style={{ flex: 1 }}
          />
          <Button onClick={() => createType.mutate()} disabled={!newTypeName.trim()}>
            Create type
          </Button>
        </Group>
      )}

      {typeId !== null && (
        <>
          <Divider />
          <TextInput
            label="Experiment name"
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
          />

          <Text fw={600}>Setup conditions</Text>
          {fields.map((f) => (
            <FieldInput
              key={f.key}
              field={f}
              value={setup[f.key]}
              onChange={(v) => setSetup((s) => ({ ...s, [f.key]: v }))}
              protocols={protocols}
            />
          ))}

          <Divider />
          <Group grow align="end">
            <DateInput
              label="Start date"
              value={startDate}
              onChange={setStartDate}
              valueFormat="YYYY-MM-DD"
            />
            <NumberInput
              label="Planned duration (days)"
              min={1}
              value={duration}
              onChange={(v) => setDuration(Number(v) || 1)}
            />
            <Select
              label="Status"
              data={meta?.statuses ?? []}
              value={status}
              onChange={(v) => setStatus(v ?? "planned")}
              allowDeselect={false}
            />
          </Group>
          <Textarea
            label="Description"
            autosize
            minRows={2}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />
          <Text size="sm" c="dimmed">
            📅 Scheduled {startStr} → {endPreview} ({duration} day(s))
          </Text>

          <Group>
            <Button
              onClick={() => save.mutate()}
              loading={save.isPending}
              disabled={!name.trim()}
            >
              💾 Save experiment
            </Button>
          </Group>

          {experiment && (
            <>
              <Divider />
              <TasksEditor experimentId={experiment.id} />
            </>
          )}
        </>
      )}
    </Stack>
  );
}

function EditTab({
  experiments,
  types,
  protocols,
  selectedId,
  setSelectedId,
}: {
  experiments: Experiment[];
  types: ExpType[];
  protocols: Protocol[];
  selectedId: number | null;
  setSelectedId: (id: number | null) => void;
}) {
  const current = experiments.find((e) => e.id === selectedId) ?? null;
  return (
    <Stack>
      <Select
        label="Editing"
        data={[
          { value: "", label: "➕ New experiment" },
          ...experiments.map((e) => ({ value: String(e.id), label: `${e.id}: ${e.name}` })),
        ]}
        value={selectedId ? String(selectedId) : ""}
        onChange={(v) => setSelectedId(v ? Number(v) : null)}
        allowDeselect={false}
        w={360}
      />
      {/* Remount the form when the target experiment or its type changes. */}
      <EditForm
        key={`${selectedId ?? "new"}-${current?.type_id ?? "none"}`}
        experiment={current}
        types={types}
        protocols={protocols}
        onSaved={() => setSelectedId(null)}
      />
    </Stack>
  );
}

// ── Types & Lists ─────────────────────────────────────────────────────────────
function TypeFieldsEditor({ type }: { type: ExpType }) {
  const { meta } = useAuth();
  const qc = useQueryClient();
  const [rows, setRows] = useState<FieldDef[]>(type.fields);

  const save = useMutation({
    mutationFn: () => api.put(`/types/${type.id}/fields`, { fields: rows }),
    onSuccess: () => {
      notifyOk("Saved field template.");
      qc.invalidateQueries({ queryKey: ["types"] });
    },
    onError: notifyErr,
  });

  const update = (i: number, patch: Partial<FieldDef>) =>
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  return (
    <Stack>
      <Text size="sm" c="dimmed">
        Edit the modular setup-condition fields. <code>kind</code> controls the
        widget; <code>vocab</code> (for select/multiselect) names the dropdown
        list.
      </Text>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>key (auto if blank)</Table.Th>
            <Table.Th>label</Table.Th>
            <Table.Th>kind</Table.Th>
            <Table.Th>vocab</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((r, i) => (
            <Table.Tr key={i}>
              <Table.Td>
                <TextInput
                  value={r.key}
                  onChange={(e) => update(i, { key: e.currentTarget.value })}
                />
              </Table.Td>
              <Table.Td>
                <TextInput
                  value={r.label}
                  onChange={(e) => update(i, { label: e.currentTarget.value })}
                />
              </Table.Td>
              <Table.Td>
                <Select
                  data={meta?.field_kinds ?? []}
                  value={r.kind}
                  onChange={(v) => update(i, { kind: v ?? "text" })}
                  allowDeselect={false}
                  w={130}
                />
              </Table.Td>
              <Table.Td>
                <Select
                  data={["", ...(meta?.vocab_categories ?? [])]}
                  value={r.vocab ?? ""}
                  onChange={(v) => update(i, { vocab: v || undefined })}
                  w={120}
                />
              </Table.Td>
              <Table.Td>
                <ActionIcon
                  color="red"
                  variant="subtle"
                  onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}
                >
                  🗑
                </ActionIcon>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      <Group>
        <Button
          size="xs"
          variant="default"
          onClick={() => setRows((rs) => [...rs, { key: "", label: "", kind: "text" }])}
        >
          ➕ Add field
        </Button>
        <Button size="xs" onClick={() => save.mutate()}>
          💾 Save fields
        </Button>
      </Group>
    </Stack>
  );
}

function VocabList({ category }: { category: string }) {
  const { meta } = useAuth();
  const qc = useQueryClient();
  const { data: terms } = useQuery<string[]>({
    queryKey: ["vocab", category],
    queryFn: () => api.get(`/vocab/${category}`),
  });
  const [val, setVal] = useState("");
  const invalidate = () => qc.invalidateQueries({ queryKey: ["vocab", category] });
  const add = useMutation({
    mutationFn: () => api.post("/vocab", { category, value: val.trim() }),
    onSuccess: () => {
      setVal("");
      invalidate();
    },
    onError: notifyErr,
  });
  const remove = useMutation({
    mutationFn: (value: string) =>
      api.del(`/vocab?category=${category}&value=${encodeURIComponent(value)}`),
    onSuccess: invalidate,
    onError: notifyErr,
  });

  return (
    <Card withBorder radius="md">
      <Text fw={600}>{meta?.vocab_category_labels[category] ?? category}</Text>
      <Stack gap={2} my="xs">
        {(terms ?? []).map((t) => (
          <Group key={t} justify="space-between">
            <Text size="sm">{t}</Text>
            <ActionIcon size="sm" variant="subtle" color="red" onClick={() => remove.mutate(t)}>
              ✕
            </ActionIcon>
          </Group>
        ))}
      </Stack>
      <Group align="end">
        <TextInput
          placeholder={`Add ${category}…`}
          value={val}
          onChange={(e) => setVal(e.currentTarget.value)}
          style={{ flex: 1 }}
        />
        <Button size="xs" onClick={() => add.mutate()} disabled={!val.trim()}>
          ➕
        </Button>
      </Group>
    </Card>
  );
}

function TypesListsTab({ types }: { types: ExpType[] }) {
  const { meta } = useAuth();
  const qc = useQueryClient();
  const [selName, setSelName] = useState<string | null>(types[0]?.name ?? null);
  const [newType, setNewType] = useState("");
  const sel = types.find((t) => t.name === selName) ?? types[0] ?? null;

  const create = useMutation({
    mutationFn: () => api.post("/types", { name: newType.trim() }),
    onSuccess: () => {
      setNewType("");
      qc.invalidateQueries({ queryKey: ["types"] });
    },
    onError: notifyErr,
  });

  return (
    <Stack>
      <Title order={4}>Experiment types & their fields</Title>
      {types.length > 0 && (
        <Select
          label="Type to edit"
          data={types.map((t) => t.name)}
          value={sel?.name ?? null}
          onChange={setSelName}
          allowDeselect={false}
          w={300}
        />
      )}
      {sel && <TypeFieldsEditor key={sel.id} type={sel} />}

      <Group align="end">
        <TextInput
          label="Add a new type"
          placeholder="e.g. Lentiviral transduction"
          value={newType}
          onChange={(e) => setNewType(e.currentTarget.value)}
          style={{ flex: 1 }}
        />
        <Button onClick={() => create.mutate()} disabled={!newType.trim()}>
          Create type
        </Button>
      </Group>

      <Divider />
      <Title order={4}>Controlled vocabulary lists</Title>
      <Group align="start" grow>
        {(meta?.vocab_categories ?? []).map((c) => (
          <VocabList key={c} category={c} />
        ))}
      </Group>
    </Stack>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────
export function Experiments() {
  const [tab, setTab] = useState<string | null>("browse");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: experiments } = useQuery<Experiment[]>({
    queryKey: ["experiments"],
    queryFn: () => api.get("/experiments"),
  });
  const { data: types } = useQuery<ExpType[]>({
    queryKey: ["types"],
    queryFn: () => api.get("/types"),
  });
  const { data: protocols } = useProtocols();

  const onEdit = (id: number) => {
    setSelectedId(id);
    setTab("edit");
  };

  const scheduled = useMemo(
    () => (experiments ?? []).filter((e) => e.start_date),
    [experiments],
  );

  return (
    <Stack>
      <Title order={2}>🧬 Experiments</Title>
      <Tabs value={tab} onChange={setTab}>
        <Tabs.List>
          <Tabs.Tab value="browse">📚 Browse</Tabs.Tab>
          <Tabs.Tab value="edit">➕ Create / Edit</Tabs.Tab>
          <Tabs.Tab value="calendar">🗓 Calendar</Tabs.Tab>
          <Tabs.Tab value="lists">⚙️ Types & Lists</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="browse" pt="md">
          <BrowseTab experiments={experiments ?? []} onEdit={onEdit} />
        </Tabs.Panel>

        <Tabs.Panel value="edit" pt="md">
          {types && (
            <EditTab
              experiments={experiments ?? []}
              types={types}
              protocols={protocols ?? []}
              selectedId={selectedId}
              setSelectedId={setSelectedId}
            />
          )}
        </Tabs.Panel>

        <Tabs.Panel value="calendar" pt="md">
          {scheduled.length === 0 ? (
            <Text c="dimmed" size="sm">
              No scheduled experiments yet. Add a start date and duration in Create
              / Edit.
            </Text>
          ) : (
            <Tabs defaultValue="gantt">
              <Tabs.List>
                <Tabs.Tab value="gantt">Timeline (Gantt)</Tabs.Tab>
                <Tabs.Tab value="month">Month grid</Tabs.Tab>
              </Tabs.List>
              <Tabs.Panel value="gantt" pt="md">
                <Gantt experiments={scheduled} />
              </Tabs.Panel>
              <Tabs.Panel value="month" pt="md">
                <MonthGrid experiments={scheduled} />
              </Tabs.Panel>
            </Tabs>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="lists" pt="md">
          <TypesListsTab types={types ?? []} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
