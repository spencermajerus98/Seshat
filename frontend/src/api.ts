// Thin fetch wrapper. Same-origin in production; cookies carry the session.
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function handle(res: Response): Promise<any> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export const api = {
  get: (path: string) =>
    fetch(`/api${path}`, { credentials: "same-origin" }).then(handle),

  post: (path: string, body?: unknown) =>
    fetch(`/api${path}`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(handle),

  put: (path: string, body?: unknown) =>
    fetch(`/api${path}`, {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(handle),

  del: (path: string) =>
    fetch(`/api${path}`, { method: "DELETE", credentials: "same-origin" }).then(
      handle,
    ),

  upload: (path: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`/api${path}`, {
      method: "POST",
      credentials: "same-origin",
      body: fd,
    }).then(handle);
  },
};
