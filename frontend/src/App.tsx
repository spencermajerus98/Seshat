import { Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import {
  AppShell,
  Badge,
  Button,
  Center,
  Group,
  Loader,
  NavLink as MantineNavLink,
  ScrollArea,
  Text,
  Title,
} from "@mantine/core";
import { useAuth } from "./auth";
import { Unlock } from "./pages/Unlock";
import { Dashboard } from "./pages/Dashboard";
import { Notebook } from "./pages/Notebook";
import { Protocols } from "./pages/Protocols";
import { Experiments } from "./pages/Experiments";
import { DailySummary } from "./pages/DailySummary";
import { ImportPage } from "./pages/ImportPage";
import { Sync } from "./pages/Sync";
import { Settings } from "./pages/Settings";

const NAV = [
  { to: "/", label: "Dashboard", icon: "📋", end: true },
  { to: "/notebook", label: "Notebook", icon: "📓" },
  { to: "/protocols", label: "Protocols", icon: "🧪" },
  { to: "/experiments", label: "Experiments", icon: "🧬" },
  { to: "/import", label: "Import", icon: "📥" },
  { to: "/sync", label: "Phone Sync", icon: "📲" },
  { to: "/summary", label: "Daily Summary", icon: "📤" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
];

export function App() {
  const { status, loading, lock } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <Center h="100vh">
        <Loader color="teal" />
      </Center>
    );
  }

  if (!status?.unlocked) {
    return <Unlock />;
  }

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 230, breakpoint: "sm" }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Text size="xl">🪶</Text>
            <Title order={3}>Seshat</Title>
          </Group>
          <Group gap="sm">
            {status.encryption ? (
              <Badge color="teal" variant="light">
                🔐 Encrypted (SQLCipher)
              </Badge>
            ) : (
              <Badge color="red" variant="light">
                ⚠️ Not encrypted
              </Badge>
            )}
            <Button size="xs" variant="default" onClick={() => lock()}>
              🔒 Lock
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm">
        <ScrollArea>
          {NAV.map((n) => (
            <MantineNavLink
              key={n.to}
              component={NavLink}
              to={n.to}
              end={n.end}
              label={n.label}
              leftSection={<span>{n.icon}</span>}
              active={
                n.end
                  ? location.pathname === n.to
                  : location.pathname.startsWith(n.to)
              }
            />
          ))}
        </ScrollArea>
      </AppShell.Navbar>

      <AppShell.Main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/notebook" element={<Notebook />} />
          <Route path="/protocols" element={<Protocols />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/sync" element={<Sync />} />
          <Route path="/summary" element={<DailySummary />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}
