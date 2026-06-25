import { useMemo, useState } from "react";
import {
  ActionIcon,
  Box,
  Button,
  Group,
  Paper,
  Select,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import type { Experiment } from "../types";
import classes from "./Calendar.module.css";

// Distinct, white-text-friendly palette. Each experiment gets a stable colour.
const PALETTE = [
  "#2f9e8f",
  "#3b82c4",
  "#8b5cf6",
  "#d97706",
  "#16a34a",
  "#dc2626",
  "#0891b2",
  "#db2777",
  "#65a30d",
  "#ca8a04",
  "#7c3aed",
  "#0d9488",
];

function cx(...parts: (string | false | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

function parse(d: string) {
  return new Date(d + "T00:00:00");
}

function ymd(d: Date) {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

function sameDay(a: Date, b: Date) {
  return ymd(a) === ymd(b);
}

function daysBetween(a: Date, b: Date) {
  return Math.round((b.getTime() - a.getTime()) / 86_400_000);
}

/** Stable colour per experiment id, assigned by sorted id so it never shifts. */
function useColorMap(experiments: Experiment[]) {
  return useMemo(() => {
    const map = new Map<number, string>();
    [...experiments]
      .sort((a, b) => a.id - b.id)
      .forEach((e, i) => map.set(e.id, PALETTE[i % PALETTE.length]));
    return map;
  }, [experiments]);
}

// ── Gantt timeline (secondary view) ───────────────────────────────────────────
export function Gantt({ experiments }: { experiments: Experiment[] }) {
  const colors = useColorMap(experiments);
  const sched = experiments.filter((e) => e.start_date);
  if (sched.length === 0) return null;
  const starts = sched.map((e) => parse(e.start_date!));
  const ends = sched.map((e) => parse(e.end_date || e.start_date!));
  const min = new Date(Math.min(...starts.map((d) => d.getTime())));
  const max = new Date(Math.max(...ends.map((d) => d.getTime())));
  const span = Math.max(daysBetween(min, max) + 1, 1);

  return (
    <Stack gap={6}>
      <Text size="xs" c="dimmed">
        {ymd(min)} → {ymd(max)}
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
                    background: colors.get(e.id),
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

type DayCell = { date: Date; inMonth: boolean };

// ── Month calendar (primary view) ─────────────────────────────────────────────
export function MonthCalendar({
  experiments,
  onSelectExperiment,
}: {
  experiments: Experiment[];
  onSelectExperiment?: (id: number) => void;
}) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth()); // 0-based
  const [selected, setSelected] = useState<string | null>(null);
  const colors = useColorMap(experiments);

  const sched = useMemo(
    () =>
      experiments
        .filter((e) => e.start_date)
        .map((e) => ({
          exp: e,
          start: parse(e.start_date!),
          end: parse(e.end_date || e.start_date!),
        })),
    [experiments],
  );

  const expsOn = (d: Date) =>
    sched.filter((s) => s.start.getTime() <= d.getTime() && d.getTime() <= s.end.getTime());

  // Build full Mon-first weeks spanning the month.
  const weeks = useMemo<DayCell[][]>(() => {
    const first = new Date(year, month, 1);
    const startOffset = (first.getDay() + 6) % 7; // Mon = 0
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const weekCount = Math.ceil((startOffset + daysInMonth) / 7);
    const gridStart = new Date(year, month, 1 - startOffset);
    const out: DayCell[][] = [];
    for (let w = 0; w < weekCount; w++) {
      const week: DayCell[] = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(gridStart);
        d.setDate(gridStart.getDate() + w * 7 + i);
        week.push({ date: d, inMonth: d.getMonth() === month });
      }
      out.push(week);
    }
    return out;
  }, [year, month]);

  const goMonth = (delta: number) => {
    const d = new Date(year, month + delta, 1);
    setYear(d.getFullYear());
    setMonth(d.getMonth());
    setSelected(null);
  };
  const goToday = () => {
    setYear(today.getFullYear());
    setMonth(today.getMonth());
    setSelected(ymd(today));
  };

  const monthName = new Date(year, month, 1).toLocaleString(undefined, { month: "long" });

  // The week to expand under the grid, if a day is selected.
  const selectedWeek = useMemo(() => {
    if (!selected) return null;
    for (const w of weeks) {
      if (w.some((c) => ymd(c.date) === selected)) return w;
    }
    return null;
  }, [selected, weeks]);

  // Experiments visible this month — for the legend.
  const legend = useMemo(() => {
    const ids = new Set<number>();
    for (const w of weeks)
      for (const c of w) if (c.inMonth) for (const s of expsOn(c.date)) ids.add(s.exp.id);
    return experiments.filter((e) => ids.has(e.id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [weeks, sched, experiments]);

  return (
    <Stack>
      <Paper withBorder radius="md" p="sm">
        <Group justify="space-between" wrap="wrap" gap="sm">
          <Group gap={6}>
            <ActionIcon variant="default" onClick={() => goMonth(-1)} aria-label="Previous month">
              ‹
            </ActionIcon>
            <Title order={4} w={170} ta="center">
              {monthName} {year}
            </Title>
            <ActionIcon variant="default" onClick={() => goMonth(1)} aria-label="Next month">
              ›
            </ActionIcon>
            <Button size="compact-sm" variant="light" onClick={goToday}>
              Today
            </Button>
          </Group>
          <Group gap="xs">
            <Select
              w={140}
              data={Array.from({ length: 12 }, (_, i) => ({
                value: String(i),
                label: new Date(2000, i, 1).toLocaleString(undefined, { month: "long" }),
              }))}
              value={String(month)}
              onChange={(v) => v !== null && (setMonth(Number(v)), setSelected(null))}
              allowDeselect={false}
            />
            <Select
              w={100}
              data={Array.from({ length: 13 }, (_, i) => String(today.getFullYear() - 6 + i))}
              value={String(year)}
              onChange={(v) => v && (setYear(Number(v)), setSelected(null))}
              allowDeselect={false}
            />
          </Group>
        </Group>
      </Paper>

      <div>
        <div className={classes.weekdayRow}>
          {WEEKDAYS.map((d) => (
            <div key={d} className={classes.weekday}>
              {d}
            </div>
          ))}
        </div>
        <div className={classes.grid}>
          {weeks.flat().map((cell, i) => {
            const isToday = sameDay(cell.date, today);
            const isWeekend = i % 7 >= 5;
            const isSelected = selected === ymd(cell.date);
            const items = expsOn(cell.date);
            return (
              <div
                key={i}
                className={cx(
                  classes.day,
                  !cell.inMonth && classes.outside,
                  isWeekend && classes.weekend,
                  isToday && classes.today,
                  isSelected && classes.selected,
                )}
                onClick={() => setSelected(ymd(cell.date))}
              >
                <span className={isToday ? classes.todayNum : classes.dayNum}>
                  {cell.date.getDate()}
                </span>
                {items.slice(0, 3).map((s) => (
                  <span
                    key={s.exp.id}
                    className={classes.chip}
                    style={{ background: colors.get(s.exp.id) }}
                    title={`${s.exp.name} · ${s.exp.status}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectExperiment?.(s.exp.id);
                    }}
                  >
                    {s.exp.name}
                  </span>
                ))}
                {items.length > 3 && (
                  <span className={classes.more}>+{items.length - 3} more</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {selectedWeek && (
        <Paper withBorder radius="md" p="sm">
          <Group justify="space-between" mb="xs">
            <Text fw={600}>
              Week of {selectedWeek[0].date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              {" – "}
              {selectedWeek[6].date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}
            </Text>
            <ActionIcon variant="subtle" onClick={() => setSelected(null)} aria-label="Collapse week">
              ✕
            </ActionIcon>
          </Group>
          <div className={classes.weekStrip}>
            {selectedWeek.map((cell) => {
              const items = expsOn(cell.date);
              const isToday = sameDay(cell.date, today);
              return (
                <div
                  key={ymd(cell.date)}
                  className={cx(classes.weekDayCard, isToday && classes.todayCard)}
                >
                  <Text size="xs" fw={700} c={isToday ? "teal" : undefined}>
                    {cell.date.toLocaleDateString(undefined, { weekday: "short" })}{" "}
                    {cell.date.getDate()}
                  </Text>
                  <Stack gap={4} mt={6}>
                    {items.length === 0 ? (
                      <Text size="xs" c="dimmed">
                        —
                      </Text>
                    ) : (
                      items.map((s) => (
                        <span
                          key={s.exp.id}
                          className={classes.weekChip}
                          style={{ background: colors.get(s.exp.id) }}
                          title={`${s.exp.name} · ${s.exp.status}`}
                          onClick={() => onSelectExperiment?.(s.exp.id)}
                        >
                          {s.exp.name}
                        </span>
                      ))
                    )}
                  </Stack>
                </div>
              );
            })}
          </div>
        </Paper>
      )}

      {legend.length > 0 && (
        <Group gap="md" mt={4}>
          {legend.map((e) => (
            <Group key={e.id} gap={6}>
              <Box w={12} h={12} style={{ borderRadius: 3, background: colors.get(e.id) }} />
              <Text size="xs">{e.name}</Text>
            </Group>
          ))}
        </Group>
      )}

      <Text size="xs" c="dimmed">
        Click a day to expand its week. Click an experiment to edit it.
      </Text>
    </Stack>
  );
}
