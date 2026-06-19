import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Accordion,
  Button,
  Code,
  Collapse,
  Group,
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
  const [showFull, { toggle }] = useDisclosure(false);
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
      {p.steps.length > 0 && (
        <div>
          <Text fw={600}>Steps</Text>
          {p.steps.map((s) => (
            <Text size="sm" key={s.step_no}>
              {s.step_no}. {s.text}
            </Text>
          ))}
        </div>
      )}
      <Group>
        <Button size="xs" variant="default" onClick={toggle}>
          {showFull ? "Hide full text" : "Full text"}
        </Button>
        <Button size="xs" color="red" variant="light" onClick={() => del.mutate()}>
          🗑 Delete protocol
        </Button>
      </Group>
      <Collapse in={showFull}>
        <Code block>{p.body_text || ""}</Code>
      </Collapse>
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
            <Accordion.Control>📄 {p.title}</Accordion.Control>
            <Accordion.Panel>
              <ProtocolBody p={p} />
            </Accordion.Panel>
          </Accordion.Item>
        ))}
      </Accordion>
    </Stack>
  );
}
