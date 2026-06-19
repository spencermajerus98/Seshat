import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Accordion,
  Button,
  Card,
  Code,
  Group,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { api } from "../api";
import { notifyErr, notifyOk } from "../lib";
import type { Entry } from "../types";

interface SyncStatus {
  inbox: string;
  pending: number;
  recent: Entry[];
}

export function Sync() {
  const qc = useQueryClient();
  const { data } = useQuery<SyncStatus>({
    queryKey: ["sync"],
    queryFn: () => api.get("/sync"),
  });

  const scan = useMutation({
    mutationFn: () => api.post("/sync/scan"),
    onSuccess: (r: { ingested: { file: string; created_at: string }[] }) => {
      notifyOk(
        r.ingested.length ? `Ingested ${r.ingested.length} note(s).` : "No new notes found.",
      );
      qc.invalidateQueries({ queryKey: ["sync"] });
      qc.invalidateQueries({ queryKey: ["entries"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: notifyErr,
  });

  return (
    <Stack>
      <Title order={2}>📲 Phone Sync</Title>

      <Card withBorder radius="md">
        <Group justify="space-between" align="start">
          <div>
            <Text fw={600}>Inbox folder</Text>
            <Code>{data?.inbox}</Code>
            <Text size="xs" c="dimmed" mt={4}>
              Keep this folder synced to your phone with Syncthing (peer-to-peer,
              no cloud).
            </Text>
          </div>
          <Paper withBorder p="md" radius="md" ta="center">
            <Text size="xl" fw={700}>
              {data?.pending ?? 0}
            </Text>
            <Text size="xs" c="dimmed">
              notes waiting
            </Text>
          </Paper>
        </Group>
        <Button mt="md" onClick={() => scan.mutate()} loading={scan.isPending}>
          🔄 Scan inbox now
        </Button>
      </Card>

      <Title order={4}>Recently ingested from phone</Title>
      {data && data.recent.length === 0 && (
        <Text c="dimmed" size="sm">
          Nothing yet. Dictate a note on your phone and save it into the synced
          folder.
        </Text>
      )}
      <Stack gap="sm">
        {data?.recent.map((e) => (
          <Paper key={e.id} withBorder p="sm" radius="md">
            <Text size="sm" fw={600}>
              {e.created_at.slice(0, 16).replace("T", " ")}
              {e.experiment_name ? ` · ${e.experiment_name}` : ""}
            </Text>
            <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
              {e.text}
            </Text>
          </Paper>
        ))}
      </Stack>

      <Accordion variant="separated">
        <Accordion.Item value="how">
          <Accordion.Control>ℹ️ How phone dictation works</Accordion.Control>
          <Accordion.Panel>
            <Text size="sm" component="div">
              <ol>
                <li>
                  On your phone, dictate (Wispr Flow / built-in dictation) or type a
                  note into a text file and save it into the Syncthing folder shared
                  with this PC.
                </li>
                <li>Syncthing copies it here automatically (peer-to-peer, end-to-end encrypted).</li>
                <li>
                  Seshat ingests new notes on launch and whenever you press <b>Scan
                  inbox now</b>, timestamps them, and files the originals under{" "}
                  <code>inbox/processed/</code>.
                </li>
              </ol>
              <Text fw={600}>Optional markers (each on its own line at the very top):</Text>
              <Code block>{`[ts: 2026-06-16T14:30]     explicit time (else the file's saved time is used)
#exp: CRISPR knock-in       link the note to an experiment by name
#type: observation          note / observation / result / deviation / task_done`}</Code>
            </Text>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  );
}
