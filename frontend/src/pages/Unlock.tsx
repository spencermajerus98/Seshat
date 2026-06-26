import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Group,
  PasswordInput,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { notifyOk } from "../lib";
import { LabBackground } from "../components/LabBackground";
import classes from "../components/Unlock.module.css";

const TAGLINES = [
  "Where every experiment finds its memory.",
  "Plan boldly. Record everything. Discover more.",
  "Turn benchwork into a story worth keeping.",
  "Your science — organized, private, encrypted.",
];

function RotatingTagline() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((n) => (n + 1) % TAGLINES.length), 4500);
    return () => clearInterval(id);
  }, []);
  return (
    <Text key={i} className={classes.tagline} c="dimmed" size="sm">
      {TAGLINES[i]}
    </Text>
  );
}

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
    <div className={classes.hero}>
      <LabBackground />
      <div className={classes.vignette} />

      <div className={classes.card}>
        <Stack gap="lg">
          <Stack gap={6} align="center" ta="center">
            <span className={classes.brandIcon}>🪶</span>
            <Title order={1} fw={800} style={{ letterSpacing: "-0.02em" }}>
              Seshat
            </Title>
            <RotatingTagline />
            <Text c="dimmed" size="xs">
              Your local, private experiment planner &amp; automatic lab notebook.
            </Text>
          </Stack>

          {status && !status.encryption && (
            <Alert color="red" variant="light">
              Encryption backend not installed — data is <b>not</b> encrypted at
              rest. Install <code>sqlcipher3-wheels</code> (see README).
            </Alert>
          )}

          {!existing && (
            <Alert color="teal" variant="light">
              No notebook found yet. Choose a strong passphrase — it encrypts your
              data and <b>cannot be recovered</b> if lost.
            </Alert>
          )}

          <form onSubmit={submit}>
            <Stack>
              <Title order={4} ta="center">
                {existing ? "Unlock your notebook" : "Create your notebook"}
              </Title>
              <PasswordInput
                size="md"
                label={existing ? "Enter your passphrase" : "Choose a passphrase"}
                value={passphrase}
                onChange={(e) => setPassphrase(e.currentTarget.value)}
                autoFocus
              />
              {!existing && (
                <PasswordInput
                  size="md"
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
              <Button type="submit" size="md" loading={busy} fullWidth mt={4}>
                {existing ? "Unlock" : "Create notebook"}
              </Button>
            </Stack>
          </form>

          <Group justify="center" gap={6}>
            <Text size="xs" c="dimmed">
              {status?.encryption ? "🔐 Encrypted at rest (SQLCipher)" : "🔓 Local only"}
            </Text>
          </Group>
        </Stack>
      </div>
    </div>
  );
}
