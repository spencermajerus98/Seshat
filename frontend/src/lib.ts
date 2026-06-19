import { notifications } from "@mantine/notifications";

export function notifyOk(message: string) {
  notifications.show({ color: "teal", message });
}

export function notifyErr(e: unknown) {
  const message = e instanceof Error ? e.message : String(e);
  notifications.show({ color: "red", title: "Error", message });
}

/** Copy rich HTML (and a plain-text fallback) so paste into Labguru keeps
 *  formatting. Falls back to plain text where ClipboardItem is unavailable. */
export async function copyRich(html: string, text: string) {
  try {
    if (navigator.clipboard && "write" in navigator.clipboard && window.ClipboardItem) {
      const item = new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" }),
      });
      await navigator.clipboard.write([item]);
    } else {
      await navigator.clipboard.writeText(text);
    }
    notifyOk("Copied — paste into Labguru.");
  } catch (e) {
    notifyErr(e);
  }
}

export async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    notifyOk("Copied to clipboard.");
  } catch (e) {
    notifyErr(e);
  }
}

export function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Inclusive end date: a 1-day experiment ends on its start date. */
export function computeEndDate(start: string | null, duration: number | null): string | null {
  if (!start) return null;
  if (!duration || duration <= 1) return start;
  const d = new Date(start + "T00:00:00");
  d.setDate(d.getDate() + (duration - 1));
  return d.toISOString().slice(0, 10);
}
