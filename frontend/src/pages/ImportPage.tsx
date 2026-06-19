import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Card,
  FileButton,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { api } from "../api";
import { notifyErr, notifyOk } from "../lib";
import type { ExcelPreview, FileEntry, Listing } from "../types";

// ── Excel → experiment mapping (shared by browse + upload) ────────────────────
function ExcelMapper({ path, name }: { path: string; name: string }) {
  const qc = useQueryClient();
  const [sheet, setSheet] = useState<string | undefined>(undefined);
  const { data: preview } = useQuery<ExcelPreview>({
    queryKey: ["excel", path, sheet],
    queryFn: () => api.post("/files/excel/parse", { path, sheet_name: sheet }),
  });
  const { data: taskFields } = useQuery<string[]>({
    queryKey: ["task-fields"],
    queryFn: () => api.get("/files/task-fields"),
  });

  const [expName, setExpName] = useState(name.replace(/\.[^.]+$/, ""));
  const [description, setDescription] = useState("");
  const [mapping, setMapping] = useState<Record<string, string | null>>({});

  // Auto-guess column mapping once the preview/fields load.
  useEffect(() => {
    if (!preview || !taskFields) return;
    setMapping((prev) => {
      if (Object.keys(prev).length) return prev;
      const guess: Record<string, string | null> = {};
      for (const f of taskFields) {
        const stem = f.split("_")[0];
        guess[f] = preview.columns.find((c) => c.toLowerCase().includes(stem)) ?? null;
      }
      return guess;
    });
  }, [preview, taskFields]);

  const doImport = useMutation({
    mutationFn: () =>
      api.post("/files/experiment/import", {
        name: expName,
        rows: preview!.rows,
        mapping,
        description: description || null,
        source_filename: name,
      }),
    onSuccess: (r: { id: number; rows: number }) => {
      notifyOk(`Imported experiment #${r.id}: ${expName} (${r.rows} task rows)`);
      qc.invalidateQueries({ queryKey: ["experiments"] });
    },
    onError: notifyErr,
  });

  if (!preview) return <Text size="sm">Reading spreadsheet…</Text>;
  const colOptions = ["(none)", ...preview.columns];

  return (
    <Stack>
      <Select
        label="Sheet"
        data={preview.sheet_names}
        value={sheet ?? preview.sheet}
        onChange={(v) => v && setSheet(v)}
        allowDeselect={false}
        w={240}
      />
      <Text fw={600}>Preview</Text>
      <div style={{ overflowX: "auto" }}>
        <Table withTableBorder striped>
          <Table.Thead>
            <Table.Tr>
              {preview.columns.map((c) => (
                <Table.Th key={c}>{c}</Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {preview.rows.slice(0, 15).map((row, i) => (
              <Table.Tr key={i}>
                {preview.columns.map((c) => (
                  <Table.Td key={c}>{row[c] == null ? "" : String(row[c])}</Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </div>

      <TextInput
        label="Experiment name"
        value={expName}
        onChange={(e) => setExpName(e.currentTarget.value)}
      />
      <TextInput
        label="Description (optional)"
        value={description}
        onChange={(e) => setDescription(e.currentTarget.value)}
      />

      <Text fw={600}>Map spreadsheet columns → task fields</Text>
      <SimpleGrid cols={{ base: 2, sm: 5 }}>
        {(taskFields ?? []).map((f) => (
          <Select
            key={f}
            label={f}
            data={colOptions}
            value={mapping[f] ?? "(none)"}
            onChange={(v) =>
              setMapping((m) => ({ ...m, [f]: v === "(none)" ? null : v }))
            }
            allowDeselect={false}
          />
        ))}
      </SimpleGrid>
      <Group>
        <Button onClick={() => doImport.mutate()} loading={doImport.isPending}>
          Import experiment
        </Button>
      </Group>
    </Stack>
  );
}

// ── Protocol preview + commit (upload flow) ──────────────────────────────────
function ProtocolCommit({ path, name }: { path: string; name: string }) {
  const qc = useQueryClient();
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
      notifyOk(`Imported protocol #${r.id}: ${r.title}`);
      qc.invalidateQueries({ queryKey: ["protocols"] });
    },
    onError: notifyErr,
  });

  if (!preview) return <Text size="sm">Parsing {name}…</Text>;
  return (
    <Stack>
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
      <Group>
        <Button onClick={() => commit.mutate()} loading={commit.isPending}>
          Import protocol
        </Button>
      </Group>
    </Stack>
  );
}

// ── Folder browser ────────────────────────────────────────────────────────────
function BrowseFolders() {
  const qc = useQueryClient();
  const { data: roots } = useQuery<{ roots: { label: string; path: string }[]; favorites: string[] }>(
    { queryKey: ["roots"], queryFn: () => api.get("/files/roots") },
  );
  const [path, setPath] = useState<string | null>(null);
  const [pathBox, setPathBox] = useState("");
  const [excel, setExcel] = useState<FileEntry | null>(null);

  // Default to the first root once it loads.
  useEffect(() => {
    if (path === null && roots?.roots.length) setPath(roots.roots[0].path);
  }, [roots, path]);

  const { data: listing } = useQuery<Listing>({
    queryKey: ["listing", path],
    queryFn: () => api.post("/files/list", { path }),
    enabled: !!path,
  });
  useEffect(() => {
    if (listing) setPathBox(listing.path);
  }, [listing]);

  const quick = useMemo(() => {
    const favs = (roots?.favorites ?? []).map((p) => ({
      label: "★ " + (p.replace(/[/\\]$/, "").split(/[/\\]/).pop() || p),
      path: p,
    }));
    return [...favs, ...(roots?.roots ?? [])];
  }, [roots]);

  const importProto = useMutation({
    mutationFn: (p: string) => api.post("/files/protocol/from-path", { path: p }),
    onSuccess: (r: { id: number }) => {
      notifyOk(`Imported protocol #${r.id}.`);
      qc.invalidateQueries({ queryKey: ["protocols"] });
    },
    onError: notifyErr,
  });

  const addFav = useMutation({
    mutationFn: () => api.post("/files/favorites", { path: listing!.path }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roots"] }),
    onError: notifyErr,
  });
  const removeFav = useMutation({
    mutationFn: () => api.del(`/files/favorites?path=${encodeURIComponent(listing!.path)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["roots"] }),
    onError: notifyErr,
  });

  return (
    <Stack>
      <Text fw={600}>Quick locations</Text>
      <Group gap="xs">
        {quick.map((q) => (
          <Button key={q.path} size="xs" variant="light" onClick={() => setPath(q.path)}>
            {q.label}
          </Button>
        ))}
      </Group>

      <Group align="end">
        <Button
          variant="default"
          disabled={!listing?.parent}
          onClick={() => listing?.parent && setPath(listing.parent)}
        >
          ⬆️ Up
        </Button>
        <TextInput
          label="Path"
          value={pathBox}
          onChange={(e) => setPathBox(e.currentTarget.value)}
          style={{ flex: 1 }}
        />
        <Button variant="default" onClick={() => setPath(pathBox)}>
          Go
        </Button>
        <Button variant="default" onClick={() => addFav.mutate()}>
          ⭐ Favorite
        </Button>
        {(roots?.favorites ?? []).includes(listing?.path ?? "") && (
          <Button variant="default" onClick={() => removeFav.mutate()}>
            Remove favorite
          </Button>
        )}
      </Group>

      <Text fw={600}>Folders</Text>
      {listing && listing.dirs.length === 0 && (
        <Text size="sm" c="dimmed">
          No subfolders.
        </Text>
      )}
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        {listing?.dirs.map((d) => (
          <Button key={d.path} size="xs" variant="subtle" justify="start" onClick={() => setPath(d.path)}>
            📁 {d.name}
          </Button>
        ))}
      </SimpleGrid>

      <Text fw={600}>Importable files</Text>
      {listing && listing.files.length === 0 && (
        <Text size="sm" c="dimmed">
          No .docx / .pdf / .txt / .md / .xlsx files here.
        </Text>
      )}
      <Stack gap="xs">
        {listing?.files.map((f) => (
          <Group key={f.path} justify="space-between">
            <Text size="sm">
              {f.is_experiment ? "🧬" : "🧪"} {f.name} · {Math.round(f.size / 1024)} KB
            </Text>
            {f.is_experiment ? (
              <Button size="xs" variant="light" onClick={() => setExcel(f)}>
                Open mapping ▶
              </Button>
            ) : (
              <Button
                size="xs"
                variant="light"
                onClick={() => importProto.mutate(f.path)}
              >
                Import protocol
              </Button>
            )}
          </Group>
        ))}
      </Stack>

      {excel && (
        <Card withBorder radius="md">
          <Title order={5} mb="sm">
            Map experiment: {excel.name}
          </Title>
          <ExcelMapper path={excel.path} name={excel.name} />
        </Card>
      )}
    </Stack>
  );
}

// ── Upload tabs ────────────────────────────────────────────────────────────────
function UploadProtocol() {
  const [staged, setStaged] = useState<{ path: string; name: string } | null>(null);
  const upload = useMutation({
    mutationFn: (file: File) => api.upload("/files/upload", file),
    onSuccess: (r: { path: string; name: string }) => setStaged(r),
    onError: notifyErr,
  });
  return (
    <Stack>
      <FileButton onChange={(f) => f && upload.mutate(f)} accept=".docx,.pdf,.txt,.md">
        {(props) => (
          <Button {...props} variant="default" loading={upload.isPending}>
            Choose a protocol file (.docx / .pdf / .txt / .md)
          </Button>
        )}
      </FileButton>
      {staged && <ProtocolCommit key={staged.path} path={staged.path} name={staged.name} />}
    </Stack>
  );
}

function UploadExcel() {
  const [staged, setStaged] = useState<{ path: string; name: string } | null>(null);
  const upload = useMutation({
    mutationFn: (file: File) => api.upload("/files/upload", file),
    onSuccess: (r: { path: string; name: string }) => setStaged(r),
    onError: notifyErr,
  });
  return (
    <Stack>
      <FileButton onChange={(f) => f && upload.mutate(f)} accept=".xlsx">
        {(props) => (
          <Button {...props} variant="default" loading={upload.isPending}>
            Choose an .xlsx experiment plan
          </Button>
        )}
      </FileButton>
      {staged && <ExcelMapper key={staged.path} path={staged.path} name={staged.name} />}
    </Stack>
  );
}

export function ImportPage() {
  return (
    <Stack>
      <Title order={2}>📥 Import</Title>
      <Text c="dimmed" size="sm">
        Seshat reads your own folders — browse and pull files straight into the
        notebook, or upload them.
      </Text>
      <Tabs defaultValue="browse">
        <Tabs.List>
          <Tabs.Tab value="browse">📁 Browse folders</Tabs.Tab>
          <Tabs.Tab value="proto">🧪 Upload protocol</Tabs.Tab>
          <Tabs.Tab value="excel">🧬 Upload experiment plan</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="browse" pt="md">
          <BrowseFolders />
        </Tabs.Panel>
        <Tabs.Panel value="proto" pt="md">
          <UploadProtocol />
        </Tabs.Panel>
        <Tabs.Panel value="excel" pt="md">
          <UploadExcel />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
