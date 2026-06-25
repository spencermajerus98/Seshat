import {
  ActionIcon,
  SegmentedControl,
  useMantineColorScheme,
} from "@mantine/core";

// Quick light/dark switch for the header.
export function ColorSchemeToggle() {
  const { colorScheme, setColorScheme } = useMantineColorScheme();
  const dark = colorScheme === "dark";
  return (
    <ActionIcon
      variant="default"
      size="lg"
      aria-label="Toggle color scheme"
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setColorScheme(dark ? "light" : "dark")}
    >
      {dark ? "☀️" : "🌙"}
    </ActionIcon>
  );
}

// Light / Dark / Auto picker for the Settings page.
export function ColorSchemeControl() {
  const { colorScheme, setColorScheme } = useMantineColorScheme();
  return (
    <SegmentedControl
      value={colorScheme}
      onChange={(v) => setColorScheme(v as "light" | "dark" | "auto")}
      data={[
        { label: "☀️ Light", value: "light" },
        { label: "🌙 Dark", value: "dark" },
        { label: "🖥 Auto", value: "auto" },
      ]}
    />
  );
}
