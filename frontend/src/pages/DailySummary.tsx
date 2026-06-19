import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Code, Group, Paper, Stack, Tabs, Text, Title } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { api } from "../api";
import { copyRich, copyText, download } from "../lib";
import type { Report } from "../types";

export function DailySummary() {
  const [date, setDate] = useState<Date>(new Date());
  const dateStr = date.toISOString().slice(0, 10);

  const { data } = useQuery<Report>({
    queryKey: ["summary", dateStr],
    queryFn: () => api.get(`/summary?date=${dateStr}`),
  });

  return (
    <Stack>
      <Title order={2}>📤 Daily Summary</Title>
      <Text c="dimmed" size="sm">
        A clean, dated recap of the day — copy it straight into your enterprise
        ELN (Labguru).
      </Text>

      <DateInput
        label="Summary date"
        value={date}
        onChange={(d) => d && setDate(d)}
        valueFormat="YYYY-MM-DD"
        w={220}
      />

      {data && (
        <Tabs defaultValue="rich">
          <Tabs.List>
            <Tabs.Tab value="rich">✨ Rich (Labguru)</Tabs.Tab>
            <Tabs.Tab value="text">Plain text</Tabs.Tab>
            <Tabs.Tab value="md">Markdown</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="rich" pt="md">
            <Stack>
              <Group>
                <Button onClick={() => copyRich(data.html, data.text)}>
                  📋 Copy (formatted)
                </Button>
                <Button
                  variant="default"
                  onClick={() =>
                    download(`labnotebook_${dateStr}.html`, data.html, "text/html")
                  }
                >
                  ⬇ Download .html
                </Button>
              </Group>
              <Card withBorder radius="md" bg="white">
                <div dangerouslySetInnerHTML={{ __html: data.html }} />
              </Card>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="text" pt="md">
            <Stack>
              <Group>
                <Button variant="default" onClick={() => copyText(data.text)}>
                  Copy
                </Button>
                <Button
                  variant="default"
                  onClick={() =>
                    download(`labnotebook_${dateStr}.txt`, data.text, "text/plain")
                  }
                >
                  ⬇ Download .txt
                </Button>
              </Group>
              <Code block>{data.text}</Code>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="md" pt="md">
            <Stack>
              <Group>
                <Button variant="default" onClick={() => copyText(data.markdown)}>
                  Copy
                </Button>
                <Button
                  variant="default"
                  onClick={() =>
                    download(`labnotebook_${dateStr}.md`, data.markdown, "text/markdown")
                  }
                >
                  ⬇ Download .md
                </Button>
              </Group>
              <Code block>{data.markdown}</Code>
            </Stack>
          </Tabs.Panel>
        </Tabs>
      )}

      {data && !data.text && (
        <Paper withBorder p="md">
          <Text c="dimmed" size="sm">
            No entries on this date — pick another, or log some on the Dashboard.
          </Text>
        </Paper>
      )}
    </Stack>
  );
}
