import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Accordion,
  Button,
  Code,
  Collapse,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { api } from "../api";
import { notifyErr, notifyOk } from "../lib";
import type { Protocol } from "../types";

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

      {p.steps.length > 0 && (
        <div>
          <Text fw={600}>Steps ({p.steps.length})</Text>
          {p.steps.map((s) => (
            <Text size="sm" key={s.step_no}>
              {s.step_no}. {s.text}
            </Text>
          ))}
        </div>
      )}

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

export function Protocols() {
  const [q, setQ] = useState("");
  const { data: protocols } = useQuery<Protocol[]>({
    queryKey: ["protocols", q],
    queryFn: () => api.get(`/protocols${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  });

  return (
    <Stack>
      <Title order={2}>🧪 Protocols</Title>
      <TextInput
        placeholder="Search protocols — title or text…"
        value={q}
        onChange={(e) => setQ(e.currentTarget.value)}
      />
      {protocols && protocols.length === 0 && (
        <Text c="dimmed" size="sm">
          No protocols yet. Add one from the <b>Import</b> page (Word, PDF, text).
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
