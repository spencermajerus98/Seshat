import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ActionIcon,
  Card,
  Group,
  Paper,
  Select,
  Stack,
  Switch,
  Text,
  Title,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { api } from "../api";
import { useAuth } from "../auth";
import { notifyErr } from "../lib";
import type { Entry } from "../types";

const ALL = "(all)";

function fmtDay(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function Notebook() {
  const { meta } = useAuth();
  const qc = useQueryClient();
  const [useDate, setUseDate] = useState(false);
  const [date, setDate] = useState<Date | null>(new Date());
  const [type, setType] = useState<string>(ALL);
  const [source, setSource] = useState<string>(ALL);

  const dateStr = useDate && date ? date.toISOString().slice(0, 10) : undefined;
  const params = new URLSearchParams();
  if (dateStr) params.set("date", dateStr);
  if (type !== ALL) params.set("entry_type", type);
  if (source !== ALL) params.set("source", source);
  params.set("limit", "500");

  const { data: entries } = useQuery<Entry[]>({
    queryKey: ["entries", dateStr, type, source],
    queryFn: () => api.get(`/notebook/entries?${params.toString()}`),
  });

  const del = useMutation({
    mutationFn: (id: number) => api.del(`/notebook/entries/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["entries"] }),
    onError: notifyErr,
  });

  let currentDay: string | null = null;

  return (
    <Stack>
      <Title order={2}>📓 Lab Notebook</Title>

      <Card withBorder radius="md">
        <Group align="end">
          <Stack gap={4}>
            <Switch
              label="Filter by date"
              checked={useDate}
              onChange={(e) => setUseDate(e.currentTarget.checked)}
            />
            {useDate && (
              <DateInput value={date} onChange={setDate} valueFormat="YYYY-MM-DD" />
            )}
          </Stack>
          <Select
            label="Type"
            data={[ALL, ...(meta?.entry_types ?? [])].map((t) => ({
              value: t,
              label: t === ALL ? ALL : meta?.entry_type_labels[t] ?? t,
            }))}
            value={type}
            onChange={(v) => setType(v ?? ALL)}
            allowDeselect={false}
          />
          <Select
            label="Source"
            data={[ALL, "app", "phone"]}
            value={source}
            onChange={(v) => setSource(v ?? ALL)}
            allowDeselect={false}
          />
        </Group>
      </Card>

      <Text c="dimmed" size="sm">
        {entries?.length ?? 0} {entries?.length === 1 ? "entry" : "entries"}
      </Text>

      <Stack gap="sm">
        {(entries ?? []).map((e) => {
          const day = e.created_at.slice(0, 10);
          const header = day !== currentDay ? ((currentDay = day), day) : null;
          return (
            <div key={e.id}>
              {header && (
                <Title order={4} mt="sm" mb={4}>
                  {fmtDay(header)}
                </Title>
              )}
              <Paper withBorder p="sm" radius="md">
                <Group justify="space-between" wrap="nowrap">
                  <Text size="sm" fw={600}>
                    {e.created_at.slice(11, 16)} ·{" "}
                    {meta?.entry_type_labels[e.entry_type] ?? e.entry_type}
                    {e.experiment_name ? ` · ${e.experiment_name}` : ""}
                    {e.source === "phone" ? " · 📲 phone" : ""}
                  </Text>
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    onClick={() => del.mutate(e.id)}
                    title="Delete entry"
                  >
                    🗑
                  </ActionIcon>
                </Group>
                <Text size="sm" mt={4} style={{ whiteSpace: "pre-wrap" }}>
                  {e.text}
                </Text>
              </Paper>
            </div>
          );
        })}
      </Stack>
    </Stack>
  );
}
