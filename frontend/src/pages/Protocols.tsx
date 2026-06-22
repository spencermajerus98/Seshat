import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Accordion,
  ActionIcon,
  Button,
  Card,
  Code,
  Collapse,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { FileButton } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { api } from "../api";
import { notifyErr, notifyOk } from "../lib";
import type { Protocol } from "../types";

// ── Steps editor — edit, reorder, add, and delete detected steps ──────────────
function StepsEditor({ p }: { p: Protocol }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);

  const begin = () => {
    setSteps(p.steps.map((s) => s.text));
    setEditing(true);
  };

  const save = useMutation({
    mutationFn: () =>
      api.put(`/protocols/${p.id}/steps`, {
        steps: steps.map((s) => s.trim()).filter(Boolean),
      }),
    onSuccess: () => {
      setEditing(false);
      notifyOk("Steps updated.");
      qc.invalidateQueries({ queryKey: ["protocols"] });
    },
    onError: notifyErr,
  });

  const setAt = (i: number, v: string) =>
    setSteps((s) => s.map((x, j) => (j === i ? v : x)));
  const removeAt = (i: number) => setSteps((s) => s.filter((_, j) => j !== i));
  const move = (i: number, dir: -1 | 1) =>
    setSteps((s) => {
      const j = i + dir;
      if (j < 0 || j >= s.length) return s;
      const next = [...s];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  const add = () => setSteps((s) => [...s, ""]);

  if (!editing) {
    return (
      <div>
        <Group justify="space-between" align="center" mb={4}>
          <Text fw={600}>Steps ({p.steps.length})</Text>
          <Button size="compact-xs" variant="subtle" onClick={begin}>
            ✏️ Edit steps
          </Button>
        </Group>
        {p.steps.length === 0 ? (
          <Text size="sm" c="dimmed">
            No steps detected. Use “Edit steps” to add them.
          </Text>
        ) : (
          p.steps.map((s) => (
            <Text size="sm" key={s.step_no}>
              {s.step_no}. {s.text}
            </Text>
          ))
        )}
      </div>
    );
  }

  return (
    <div>
      <Text fw={600} mb={4}>
        Editing steps
      </Text>
      <Stack gap="xs">
        {steps.map((s, i) => (
          <Group key={i} gap="xs" wrap="nowrap" align="center">
            <Text size="sm" c="dimmed" w={22} ta="right">
              {i + 1}.
            </Text>
            <TextInput
              value={s}
              onChange={(e) => setAt(i, e.currentTarget.value)}
              style={{ flex: 1 }}
              placeholder="Step text…"
            />
            <ActionIcon
              variant="subtle"
              color="gray"
              disabled={i === 0}
              onClick={() => move(i, -1)}
              aria-label="Move up"
            >
              ↑
            </ActionIcon>
            <ActionIcon
              variant="subtle"
              color="gray"
              disabled={i === steps.length - 1}
              onClick={() => move(i, 1)}
              aria-label="Move down"
            >
              ↓
            </ActionIcon>
            <ActionIcon
              variant="subtle"
              color="red"
              onClick={() => removeAt(i)}
              aria-label="Delete step"
            >
              🗑
            </ActionIcon>
          </Group>
        ))}
      </Stack>
      <Group mt="sm">
        <Button size="xs" variant="default" onClick={add}>
          ＋ Add step
        </Button>
        <Button size="xs" onClick={() => save.mutate()} loading={save.isPending}>
          Save steps
        </Button>
        <Button size="xs" variant="subtle" onClick={() => setEditing(false)}>
          Cancel
        </Button>
      </Group>
    </div>
  );
}

function ProtocolBody({ p }: { p: Protocol }) {
  const qc = useQueryClient();
  const [showFull, { toggle: toggleFull }] = useDisclosure(false);
  const [viewerOpen, { open: openViewer, close: closeViewer }] = useDisclosure(false);
  const [renaming, setRenaming] = useState(false);
  const [newTitle, setNewTitle] = useState(p.title);

  const rename = useMutation({
    mutationFn: () => api.put(`/protocols/${p.id}`, { title: newTitle.trim() }),
    onSuccess: () => {
      setRenaming(false);
      notifyOk("Protocol renamed.");
      qc.invalidateQueries({ queryKey: ["protocols"] });
    },
    onError: notifyErr,
  });

  const del = useMutation({
    mutationFn: () => api.del(`/protocols/${p.id}`),
    onSuccess: () => {
      notifyOk("Protocol deleted.");
      qc.invalidateQueries({ queryKey: ["protocols"] });
    },
    onError: notifyErr,
  });

  const meta = [
    p.source_filename ? `file: ${p.source_filename}` : null,
    p.version ? `version: ${p.version}` : null,
    `imported: ${p.imported_at.slice(0, 10)}`,
  ].filter(Boolean);

  return (
    <Stack>
      <Text size="xs" c="dimmed">
        {meta.join(" · ")}
      </Text>

      {renaming && (
        <Group align="end">
          <TextInput
            value={newTitle}
            onChange={(e) => setNewTitle(e.currentTarget.value)}
            style={{ flex: 1 }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && newTitle.trim()) rename.mutate();
              if (e.key === "Escape") { setRenaming(false); setNewTitle(p.title); }
            }}
            autoFocus
          />
          <Button size="xs" onClick={() => rename.mutate()} disabled={!newTitle.trim()} loading={rename.isPending}>
            Save
          </Button>
          <Button size="xs" variant="default" onClick={() => { setRenaming(false); setNewTitle(p.title); }}>
            Cancel
          </Button>
        </Group>
      )}

      <StepsEditor p={p} />

      <Group>
        {p.has_file && (
          <Button size="xs" variant="light" onClick={openViewer}>
            📄 View document
          </Button>
        )}
        <Button size="xs" variant="default" onClick={toggleFull}>
          {showFull ? "Hide full text" : "Full text"}
        </Button>
        <Button size="xs" variant="default" onClick={() => { setRenaming(!renaming); setNewTitle(p.title); }}>
          ✏️ Rename
        </Button>
        <Button size="xs" color="red" variant="light" onClick={() => del.mutate()} loading={del.isPending}>
          🗑 Delete
        </Button>
      </Group>

      <Collapse in={showFull}>
        <Code block>{p.body_text || ""}</Code>
      </Collapse>

      <Modal
        opened={viewerOpen}
        onClose={closeViewer}
        title={p.title}
        size="90%"
        styles={{ body: { padding: 0 } }}
      >
        <iframe
          src={`/api/protocols/${p.id}/file`}
          title={p.title}
          style={{ width: "100%", height: "80vh", border: "none", display: "block" }}
        />
      </Modal>
    </Stack>
  );
}

// ── Import (drag & drop + button) directly on the Protocols tab ───────────────
const PROTO_ACCEPT = ".docx,.pdf,.txt,.md,.markdown";

function ProtocolImport() {
  const qc = useQueryClient();
  const [staged, setStaged] = useState<{ path: string; name: string } | null>(null);
  const [dragging, setDragging] = useState(false);

  const upload = useMutation({
    mutationFn: (file: File) => api.upload("/files/upload", file),
    onSuccess: (r: { path: string; name: string }) => setStaged(r),
    onError: notifyErr,
  });

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) upload.mutate(file);
  };

  return (
    <Card withBorder radius="md">
      <Title order={5} mb="xs">
        Import a protocol
      </Title>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${dragging ? "#228be6" : "#ccc"}`,
          borderRadius: 8,
          padding: "1.5rem",
          textAlign: "center",
          background: dragging ? "rgba(34,139,230,0.06)" : "transparent",
          transition: "background 120ms, border-color 120ms",
        }}
      >
        <Text size="sm" c="dimmed" mb="xs">
          {upload.isPending
            ? "Uploading…"
            : "Drag & drop a .docx / .pdf / .txt / .md file here"}
        </Text>
        <FileButton onChange={(f) => f && upload.mutate(f)} accept={PROTO_ACCEPT}>
          {(props) => (
            <Button {...props} size="xs" variant="light" loading={upload.isPending}>
              Or choose a file…
            </Button>
          )}
        </FileButton>
      </div>
      {staged && (
        <ProtocolCommit
          key={staged.path}
          path={staged.path}
          name={staged.name}
          onDone={() => {
            setStaged(null);
            qc.invalidateQueries({ queryKey: ["protocols"] });
          }}
        />
      )}
    </Card>
  );
}

function ProtocolCommit({
  path,
  name,
  onDone,
}: {
  path: string;
  name: string;
  onDone: () => void;
}) {
  const { data: preview } = useQuery<{ title: string; steps: string[]; step_count: number }>({
    queryKey: ["proto-preview", path],
    queryFn: () => api.post("/files/protocol/preview", { path }),
  });
  const [title, setTitle] = useState("");
  const [version, setVersion] = useState("");
  const [tags, setTags] = useState("");
  useEffect(() => {
    if (preview && !title) setTitle(preview.title);
  }, [preview]); // eslint-disable-line react-hooks/exhaustive-deps

  const commit = useMutation({
    mutationFn: () =>
      api.post("/files/protocol/commit", {
        path,
        title,
        version: version || null,
        tags: tags || null,
      }),
    onSuccess: (r: { id: number; title: string }) => {
      notifyOk(`Imported protocol #${r.id}: ${r.title}. Edit its steps below.`);
      onDone();
    },
    onError: notifyErr,
  });

  if (!preview) return <Text size="sm" mt="sm">Parsing {name}…</Text>;
  return (
    <Stack mt="md">
      <TextInput label="Title" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
      <Group grow>
        <TextInput
          label="Version (optional)"
          value={version}
          onChange={(e) => setVersion(e.currentTarget.value)}
        />
        <TextInput
          label="Tags (optional, comma-separated)"
          value={tags}
          onChange={(e) => setTags(e.currentTarget.value)}
        />
      </Group>
      <Text fw={600}>Detected {preview.step_count} step(s):</Text>
      <Stack gap={2}>
        {preview.steps.slice(0, 20).map((s, i) => (
          <Text size="sm" key={i}>
            {i + 1}. {s}
          </Text>
        ))}
        {preview.step_count > 20 && (
          <Text size="xs" c="dimmed">
            …and {preview.step_count - 20} more
          </Text>
        )}
      </Stack>
      <Text size="xs" c="dimmed">
        Steps can be edited, reordered, added, or deleted after import.
      </Text>
      <Group>
        <Button onClick={() => commit.mutate()} loading={commit.isPending}>
          Import protocol
        </Button>
      </Group>
    </Stack>
  );
}

export function Protocols() {
  const [q, setQ] = useState("");
  const { data: protocols } = useQuery<Protocol[]>({
    queryKey: ["protocols", q],
    queryFn: () => api.get(`/protocols${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  });

  return (
    <Stack>
      <Title order={2}>🧪 Protocols</Title>

      <ProtocolImport />

      <TextInput
        placeholder="Search protocols — title or text…"
        value={q}
        onChange={(e) => setQ(e.currentTarget.value)}
      />
      {protocols && protocols.length === 0 && (
        <Text c="dimmed" size="sm">
          No protocols yet. Import one above, or from the <b>Import</b> page.
        </Text>
      )}
      <Accordion variant="separated">
        {(protocols ?? []).map((p) => (
          <Accordion.Item key={p.id} value={String(p.id)}>
            <Accordion.Control>
              📄 {p.title}
              {p.has_file && (
                <Text span size="xs" c="dimmed" ml={8}>
                  · {p.source_filename?.endsWith(".pdf") ? "PDF" : "DOCX"}
                </Text>
              )}
            </Accordion.Control>
            <Accordion.Panel>
              <ProtocolBody p={p} />
            </Accordion.Panel>
          </Accordion.Item>
        ))}
      </Accordion>
    </Stack>
  );
}
