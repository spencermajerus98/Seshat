import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Card,
  Divider,
  Grid,
  Group,
  Paper,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { api } from "../api";
import { useAuth } from "../auth";
import { notifyErr, notifyOk } from "../lib";
import type { Dashboard as DashboardData, Experiment } from "../types";

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <Paper withBorder p="md" radius="md">
      <Text size="xl" fw={700}>
        {value}
      </Text>
      <Text c="dimmed" size="sm">
        {label}
      </Text>
    </Paper>
  );
}

export function Dashboard() {
  const { meta } = useAuth();
  const qc = useQueryClient();
  const { data } = useQuery<DashboardData>({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/dashboard"),
  });
  const { data: experiments } = useQuery<Experiment[]>({
    queryKey: ["experiments"],
    queryFn: () => api.get("/experiments"),
  });

  const [text, setText] = useState("");
  const [entryType, setEntryType] = useState("note");
  const [expId, setExpId] = useState<string | null>(null);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["dashboard"] });
    qc.invalidateQueries({ queryKey: ["entries"] });
  };

  const log = useMutation({
    mutationFn: () =>
      api.post("/notebook/entries", {
        text,
        entry_type: entryType,
        experiment_id: expId ? Number(expId) : null,
      }),
    onSuccess: () => {
      setText("");
      notifyOk("Logged.");
      invalidate();
    },
    onError: notifyErr,
  });

  const complete = useMutation({
    mutationFn: (id: number) => api.post(`/dashboard/tasks/${id}/complete`),
    onSuccess: invalidate,
    onError: notifyErr,
  });

  return (
    <Stack>
      <Title order={2}>📋 Dashboard</Title>

      <Grid>
        <Grid.Col span={{ base: 6, sm: 3 }}>
          <Metric label="Entries today" value={data?.entries_today ?? 0} />
        </Grid.Col>
        <Grid.Col span={{ base: 6, sm: 3 }}>
          <Metric label="Protocols" value={data?.protocols ?? 0} />
        </Grid.Col>
        <Grid.Col span={{ base: 6, sm: 3 }}>
          <Metric label="Experiments" value={data?.experiments ?? 0} />
        </Grid.Col>
        <Grid.Col span={{ base: 6, sm: 3 }}>
          <Metric label="Phone notes waiting" value={data?.pending_notes ?? 0} />
        </Grid.Col>
      </Grid>

      <Card withBorder radius="md">
        <Title order={4}>Quick log</Title>
        <Text c="dimmed" size="sm" mb="sm">
          Logged with the exact date & time automatically — you never type a
          timestamp.
        </Text>
        <Stack>
          <Textarea
            placeholder="What did you just do / observe?"
            autosize
            minRows={3}
            value={text}
            onChange={(e) => setText(e.currentTarget.value)}
          />
          <Group grow align="end">
            <Select
              label="Type"
              data={(meta?.entry_types ?? []).map((t) => ({
                value: t,
                label: meta?.entry_type_labels[t] ?? t,
              }))}
              value={entryType}
              onChange={(v) => setEntryType(v ?? "note")}
              allowDeselect={false}
            />
            <Select
              label="Link to experiment (optional)"
              data={(experiments ?? []).map((e) => ({
                value: String(e.id),
                label: e.name,
              }))}
              value={expId}
              onChange={setExpId}
              clearable
              searchable
            />
          </Group>
          <Group justify="flex-end">
            <Button
              onClick={() => log.mutate()}
              loading={log.isPending}
              disabled={!text.trim()}
            >
              Log entry
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder radius="md">
        <Title order={4}>Pending experiment tasks</Title>
        <Divider my="sm" />
        {data && data.pending_tasks.length === 0 && (
          <Text c="dimmed" size="sm">
            No pending tasks. Import an experiment plan from <b>Import</b> to
            populate this.
          </Text>
        )}
        <Stack gap="xs">
          {data?.pending_tasks.map((t) => (
            <Group key={t.id} justify="space-between" wrap="nowrap">
              <div>
                <Text fw={600}>{t.task_name}</Text>
                <Text size="xs" c="dimmed">
                  {[t.experiment_name, t.planned_date, t.sample]
                    .filter(Boolean)
                    .join(" · ")}
                </Text>
              </div>
              <Button
                size="xs"
                variant="light"
                onClick={() => complete.mutate(t.id)}
              >
                ✅ Done
              </Button>
            </Group>
          ))}
        </Stack>
      </Card>

      <Card withBorder radius="md">
        <Title order={4}>Today's entries</Title>
        <Divider my="sm" />
        {data && data.today_entries.length === 0 && (
          <Text c="dimmed" size="sm">
            Nothing logged yet today.
          </Text>
        )}
        <Stack gap="sm">
          {data?.today_entries.map((e) => (
            <div key={e.id}>
              <Text size="sm" fw={600}>
                {e.created_at.slice(11, 16)} · {meta?.entry_type_labels[e.entry_type] ?? e.entry_type}
                {e.experiment_name ? ` · ${e.experiment_name}` : ""}
                {e.source === "phone" ? " · 📲 phone" : ""}
              </Text>
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                {e.text}
              </Text>
            </div>
          ))}
        </Stack>
      </Card>
    </Stack>
  );
}
