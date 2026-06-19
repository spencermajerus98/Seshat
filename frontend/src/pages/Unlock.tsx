import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Center,
  PasswordInput,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { notifyOk } from "../lib";

export function Unlock() {
  const { status, refresh } = useAuth();
  const existing = status?.db_exists ?? false;
  const [passphrase, setPassphrase] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    if (!passphrase) return setErr("Please enter a passphrase.");
    if (!existing && passphrase !== confirm)
      return setErr("Passphrases do not match.");
    setBusy(true);
    try {
      const r = await api.post("/auth/unlock", {
        passphrase,
        confirm: existing ? undefined : confirm,
      });
      if (r.ingested) notifyOk(`📥 Ingested ${r.ingested} note(s) from your phone inbox.`);
      await refresh();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not open the notebook.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Center h="100vh" bg="var(--mantine-color-gray-0)">
      <Card shadow="md" radius="md" withBorder w={420} p="xl">
        <Stack>
          <div>
            <Title order={2}>🪶 Seshat</Title>
            <Text c="dimmed" size="sm">
              Your local, private experiment planner & automatic lab notebook.
            </Text>
          </div>

          {status && !status.encryption && (
            <Alert color="red" variant="light">
              Encryption backend not installed — data is <b>not</b> encrypted at
              rest. Install <code>sqlcipher3-wheels</code> (see README).
            </Alert>
          )}

          <Title order={4}>{existing ? "Unlock your notebook" : "Create your notebook"}</Title>

          {!existing && (
            <Alert color="teal" variant="light">
              No notebook found yet. Choose a strong passphrase — it encrypts your
              data and <b>cannot be recovered</b> if lost.
            </Alert>
          )}

          <form onSubmit={submit}>
            <Stack>
              <PasswordInput
                label={existing ? "Enter your passphrase" : "Choose a passphrase"}
                value={passphrase}
                onChange={(e) => setPassphrase(e.currentTarget.value)}
                autoFocus
              />
              {!existing && (
                <PasswordInput
                  label="Confirm passphrase"
                  value={confirm}
                  onChange={(e) => setConfirm(e.currentTarget.value)}
                />
              )}
              {err && (
                <Text c="red" size="sm">
                  {err}
                </Text>
              )}
              <Button type="submit" loading={busy} fullWidth>
                Open notebook
              </Button>
            </Stack>
          </form>
        </Stack>
      </Card>
    </Center>
  );
}
