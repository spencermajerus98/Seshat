import { useEffect, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { api } from "../api";
import { notifyErr, notifyOk } from "../lib";

interface SettingsData {
  db_path: string;
  inbox_dir: string;
  encryption: boolean;
  db_exists: boolean;
}

export function Settings() {
  const { data } = useQuery<SettingsData>({
    queryKey: ["settings"],
    queryFn: () => api.get("/settings"),
  });

  const [dbPath, setDbPath] = useState("");
  const [inbox, setInbox] = useState("");
  useEffect(() => {
    if (data) {
      setDbPath(data.db_path);
      setInbox(data.inbox_dir);
    }
  }, [data]);

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");

  const savePaths = useMutation({
    mutationFn: () => api.put("/settings", { db_path: dbPath, inbox_dir: inbox }),
    onSuccess: () =>
      notifyOk("Saved. Changing the database file takes effect after you lock & reopen."),
    onError: notifyErr,
  });

  const changePass = useMutation({
    mutationFn: () =>
      api.post("/auth/passphrase", {
        current,
        new_passphrase: next,
        confirm,
      }),
    onSuccess: () => {
      setCurrent("");
      setNext("");
      setConfirm("");
      notifyOk("Passphrase updated.");
    },
    onError: notifyErr,
  });

  const backup = () => {
    window.location.href = "/api/settings/backup";
  };
  const exportMd = async () => {
    const md = await api.get("/settings/export");
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "seshat_notebook_export.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Stack>
      <Title order={2}>⚙️ Settings</Title>

      <Card withBorder radius="md">
        <Title order={4}>Folders</Title>
        <Stack mt="sm">
          <TextInput
            label="Database file"
            value={dbPath}
            onChange={(e) => setDbPath(e.currentTarget.value)}
          />
          <TextInput
            label="Phone inbox folder (Syncthing)"
            value={inbox}
            onChange={(e) => setInbox(e.currentTarget.value)}
          />
          <Group>
            <Button onClick={() => savePaths.mutate()}>Save paths</Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder radius="md">
        <Title order={4}>Change passphrase</Title>
        {data && !data.encryption && (
          <Alert color="orange" variant="light" mt="sm">
            Encryption backend not installed — the passphrase guards access but the
            file is not encrypted.
          </Alert>
        )}
        <Stack mt="sm">
          <PasswordInput
            label="Current passphrase"
            value={current}
            onChange={(e) => setCurrent(e.currentTarget.value)}
          />
          <PasswordInput
            label="New passphrase"
            value={next}
            onChange={(e) => setNext(e.currentTarget.value)}
          />
          <PasswordInput
            label="Confirm new passphrase"
            value={confirm}
            onChange={(e) => setConfirm(e.currentTarget.value)}
          />
          <Group>
            <Button onClick={() => changePass.mutate()} loading={changePass.isPending}>
              Update passphrase
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder radius="md">
        <Title order={4}>Backup & export</Title>
        <Text size="sm" c="dimmed" mt={4}>
          {data?.encryption
            ? "The database file is encrypted at rest."
            : "This database file is NOT encrypted."}{" "}
          Store backups somewhere that meets your lab's security policy.
        </Text>
        <Group mt="sm">
          <Button variant="default" onClick={backup} disabled={!data?.db_exists}>
            ⬇ Download database backup
          </Button>
          <Button variant="default" onClick={exportMd}>
            ⬇ Export all entries to Markdown
          </Button>
        </Group>
      </Card>
    </Stack>
  );
}
