function apiBase(): string {
  const pub = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (pub) {
    return pub;
  }
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000";
  }
  return "";
}

export function apiUrl(path: string): string {
  const base = apiBase();
  if (base) {
    return `${base}${path.startsWith("/") ? path : `/${path}`}`;
  }
  return `/api${path.startsWith("/") ? path : `/${path}`}`;
}

export type Monitor = {
  id: number;
  name: string;
  url: string;
  interval_seconds: number;
  timeout_seconds: number;
  failure_threshold: number;
  consecutive_failures: number;
  last_status: string | null;
  last_checked_at: string | null;
  created_at: string;
};

export type Sla = {
  monitor_id: number;
  window: string;
  uptime_percent: number;
  total_checks: number;
  successful_checks: number;
};

export type CheckResult = {
  id: number;
  ok: boolean;
  status_code: number | null;
  latency_ms: number | null;
  error_message: string | null;
  checked_at: string;
};

export type Incident = {
  id: number;
  monitor_id: number;
  title: string;
  summary: string;
  status: string;
  detected_by: string;
  started_at: string;
  resolved_at: string | null;
};

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return (await res.json()) as T;
}

export async function fetchMonitors(): Promise<Monitor[]> {
  const res = await fetch(apiUrl("/monitors"), { cache: "no-store" });
  return parseJson<Monitor[]>(res);
}

export async function createMonitor(payload: {
  name: string;
  url: string;
  interval_seconds: number;
  timeout_seconds: number;
  failure_threshold: number;
}): Promise<Monitor> {
  const res = await fetch(apiUrl("/monitors"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<Monitor>(res);
}

export async function deleteMonitor(id: number): Promise<void> {
  const res = await fetch(apiUrl(`/monitors/${id}`), { method: "DELETE" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
}

export async function fetchSla(id: number, window: "24h" | "7d"): Promise<Sla> {
  const res = await fetch(apiUrl(`/monitors/${id}/sla?window=${window}`), { cache: "no-store" });
  return parseJson<Sla>(res);
}

export async function fetchChecks(id: number): Promise<CheckResult[]> {
  const res = await fetch(apiUrl(`/monitors/${id}/checks?limit=120`), { cache: "no-store" });
  return parseJson<CheckResult[]>(res);
}

export async function fetchIncidents(): Promise<Incident[]> {
  const res = await fetch(apiUrl("/incidents"), { cache: "no-store" });
  return parseJson<Incident[]>(res);
}

export async function resolveIncident(id: number): Promise<Incident> {
  const res = await fetch(apiUrl(`/incidents/${id}/resolve`), { method: "POST" });
  return parseJson<Incident>(res);
}
