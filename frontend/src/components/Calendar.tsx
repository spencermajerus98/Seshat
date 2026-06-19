import { useState } from "react";
import { Box, Group, Paper, Select, Stack, Text, Title } from "@mantine/core";
import type { Experiment } from "../types";

const PALETTE = ["#2f9e8f", "#3b82c4", "#b07cc6", "#d98a3d", "#5aa469", "#c75c6a"];

function colorFor(key: string, keys: string[]): string {
  const idx = keys.indexOf(key);
  return PALETTE[(idx < 0 ? 0 : idx) % PALETTE.length];
}

function parse(d: string) {
  return new Date(d + "T00:00:00");
}

function daysBetween(a: Date, b: Date) {
  return Math.round((b.getTime() - a.getTime()) / 86_400_000);
}

export function Gantt({ experiments }: { experiments: Experiment[] }) {
  const sched = experiments.filter((e) => e.start_date);
  const typeKeys = Array.from(new Set(sched.map((e) => e.type_name || "—")));
  const starts = sched.map((e) => parse(e.start_date!));
  const ends = sched.map((e) => parse(e.end_date || e.start_date!));
  const min = new Date(Math.min(...starts.map((d) => d.getTime())));
  const max = new Date(Math.max(...ends.map((d) => d.getTime())));
  const span = Math.max(daysBetween(min, max) + 1, 1);

  return (
    <Stack gap={6}>
      <Group gap="md">
        {typeKeys.map((t) => (
          <Group key={t} gap={4}>
            <Box w={12} h={12} bg={colorFor(t, typeKeys)} style={{ borderRadius: 3 }} />
            <Text size="xs">{t}</Text>
          </Group>
        ))}
      </Group>
      <Text size="xs" c="dimmed">
        {min.toISOString().slice(0, 10)} → {max.toISOString().slice(0, 10)}
      </Text>
      <Stack gap={4}>
        {sched.map((e) => {
          const s = parse(e.start_date!);
          const en = parse(e.end_date || e.start_date!);
          const offset = (daysBetween(min, s) / span) * 100;
          const width = ((daysBetween(s, en) + 1) / span) * 100;
          return (
            <Group key={e.id} gap="sm" wrap="nowrap">
              <Text size="xs" w={150} truncate title={e.name}>
                {e.name}
              </Text>
              <Box style={{ position: "relative", flex: 1, height: 22 }}>
                <Box
                  style={{
                    position: "absolute",
                    left: `${offset}%`,
                    width: `${width}%`,
                    height: 18,
                    top: 2,
                    background: colorFor(e.type_name || "—", typeKeys),
                    borderRadius: 4,
                  }}
                  title={`${e.name} · ${e.start_date} → ${e.end_date || e.start_date} · ${e.status}`}
                />
              </Box>
            </Group>
          );
        })}
      </Stack>
    </Stack>
  );
}

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function MonthGrid({ experiments }: { experiments: Experiment[] }) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth()); // 0-based

  const sched = experiments
    .filter((e) => e.start_date)
    .map((e) => ({
      name: e.name,
      start: parse(e.start_date!),
      end: parse(e.end_date || e.start_date!),
    }));

  // Build weeks (Mon-first) covering the month.
  const first = new Date(year, month, 1);
  const startOffset = (first.getDay() + 6) % 7; // Mon=0
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < startOffset; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const monthName = new Date(year, month, 1).toLocaleString(undefined, {
    month: "long",
  });

  return (
    <Stack>
      <Group>
        <Select
          label="Year"
          w={110}
          data={Array.from({ length: 11 }, (_, i) => String(today.getFullYear() - 5 + i))}
          value={String(year)}
          onChange={(v) => v && setYear(Number(v))}
          allowDeselect={false}
        />
        <Select
          label="Month"
          w={150}
          data={Array.from({ length: 12 }, (_, i) => ({
            value: String(i),
            label: new Date(2000, i, 1).toLocaleString(undefined, { month: "long" }),
          }))}
          value={String(month)}
          onChange={(v) => v !== null && setMonth(Number(v))}
          allowDeselect={false}
        />
      </Group>
      <Title order={4}>
        {monthName} {year}
      </Title>
      <Group gap={0} grow>
        {WEEKDAYS.map((d) => (
          <Text key={d} fw={700} size="sm" ta="center">
            {d}
          </Text>
        ))}
      </Group>
      <Box
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: 4,
        }}
      >
        {cells.map((day, i) => {
          if (day === null) return <Box key={i} />;
          const d = new Date(year, month, day);
          const names = sched.filter((s) => s.start <= d && d <= s.end).map((s) => s.name);
          return (
            <Paper key={i} withBorder p={4} mih={70}>
              <Text size="xs" fw={600}>
                {day}
              </Text>
              <Stack gap={2} mt={2}>
                {names.map((n, j) => (
                  <Text
                    key={j}
                    size="10px"
                    style={{
                      background: "#e3efe8",
                      borderRadius: 4,
                      padding: "1px 4px",
                      lineHeight: 1.3,
                    }}
                    truncate
                    title={n}
                  >
                    {n}
                  </Text>
                ))}
              </Stack>
            </Paper>
          );
        })}
      </Box>
    </Stack>
  );
}
