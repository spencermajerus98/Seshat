import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { AuthStatus, Meta } from "./types";

interface AuthCtx {
  status: AuthStatus | null;
  meta: Meta | null;
  loading: boolean;
  refresh: () => Promise<void>;
  lock: () => Promise<void>;
}

const Ctx = createContext<AuthCtx>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const s = await api.get("/auth/status");
    setStatus(s);
  };

  const lock = async () => {
    await api.post("/auth/lock");
    await refresh();
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  // Meta constants only make sense (and only fetch) once unlocked.
  const { data: meta } = useQuery<Meta>({
    queryKey: ["meta"],
    queryFn: () => api.get("/meta"),
    enabled: !!status?.unlocked,
  });

  return (
    <Ctx.Provider value={{ status, meta: meta ?? null, loading, refresh, lock }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
