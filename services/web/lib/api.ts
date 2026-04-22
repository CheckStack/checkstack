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

export type Tag = {
  id: number;
  name: string;
  color: string | null;
  created_at: string;
};

export type TagRef = {
  id: number;
  name: string;
  color: string | null;
};

export type Monitor = {
  id: number;
  name: string;
  url: string;
  interval_seconds: number;
  timeout_seconds: number;
  failure_threshold: number;
  consecutive_failures: number;
  alerts_enabled: boolean;
  last_status: string | null;
  last_checked_at: string | null;
  tls_cert_expires_at: string | null;
  tls_cert_subject: string | null;
  tls_cert_checked_at: string | null;
  tls_cert_probe_error: string | null;
  tags: TagRef[];
  alerts_will_fire: boolean;
  created_at: string;
};

export type Sla = {
  monitor_id: number;
  window: string;
  uptime_percent: number;
  total_checks: number;
  successful_checks: number;
};

export type MonitorStats = {
  monitor_id: number;
  window: string;
  avg_latency_ms: number | null;
  p95_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
  total_checks: number;
  with_latency: number;
  sla: Sla;
};

export type UptimePoint = {
  t: string;
  status: "success" | "failure";
  ok: boolean;
  response_time_ms: number | null;
  status_code: number | null;
};

export type UptimeSeries = {
  monitor_id: number;
  range: string;
  from: string;
  to: string;
  points: UptimePoint[];
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
  duration_seconds: number | null;
};

export type IncidentDetail = Incident & {
  start_time: string;
  end_time: string | null;
  monitor_name: string;
  monitor_url: string;
  monitor: {
    id: number;
    name: string;
    url: string;
    alerts_enabled: boolean;
  };
  failure_reason_summary: string | null;
  uptime_logs: {
    timestamp: string;
    status: "UP" | "DOWN" | string;
    response_time_ms: number | null;
    error_message: string | null;
  }[];
};

export type PublicMonitor = {
  id: number;
  name: string;
  url: string;
  status: string;
  sla_24h_percent: number;
};

export type PublicStatusResponse = { monitors: PublicMonitor[] };

export type AlertConfig = {
  id: number;
  kind: "slack" | "email";
  name: string;
  config: Record<string, unknown>;
  enabled: boolean;
  monitor_id: number | null;
  created_at: string;
};

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return (await res.json()) as T;
}

export async function fetchMonitors(tagId?: number | null): Promise<Monitor[]> {
  const q = tagId != null && tagId > 0 ? `?tag_id=${tagId}` : "";
  const res = await fetch(apiUrl(`/monitors${q}`), { cache: "no-store" });
  return parseJson<Monitor[]>(res);
}

export async function fetchMonitor(id: number): Promise<Monitor> {
  const res = await fetch(apiUrl(`/monitors/${id}`), { cache: "no-store" });
  return parseJson<Monitor>(res);
}

export async function createMonitor(payload: {
  name: string;
  url: string;
  interval_seconds: number;
  timeout_seconds: number;
  failure_threshold: number;
  alerts_enabled?: boolean;
  tag_ids?: number[];
}): Promise<Monitor> {
  const res = await fetch(apiUrl("/monitors"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      alerts_enabled: true,
      tag_ids: [],
      ...payload,
    }),
  });
  return parseJson<Monitor>(res);
}

export async function updateMonitor(
  id: number,
  payload: Partial<{
    name: string;
    url: string;
    interval_seconds: number;
    timeout_seconds: number;
    failure_threshold: number;
    alerts_enabled: boolean;
    tag_ids: number[];
  }>,
): Promise<Monitor> {
  const res = await fetch(apiUrl(`/monitors/${id}`), {
    method: "PATCH",
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

export async function fetchMonitorStats(id: number, window: "24h" | "7d" = "24h"): Promise<MonitorStats> {
  const res = await fetch(apiUrl(`/monitors/${id}/stats?window=${window}`), { cache: "no-store" });
  return parseJson<MonitorStats>(res);
}

export async function fetchUptime(
  id: number,
  range: "1h" | "24h" | "7d" | "30d" = "24h",
): Promise<UptimeSeries> {
  const res = await fetch(apiUrl(`/uptime/${id}?range=${encodeURIComponent(range)}`), { cache: "no-store" });
  const j = await parseJson<{
    monitor_id: number;
    range: string;
    from: string;
    to: string;
    points: (UptimePoint & { t: string })[];
  }>(res);
  return { ...j, points: j.points.map((p) => ({ ...p, t: String(p.t) })) };
}

export async function fetchChecks(id: number): Promise<CheckResult[]> {
  const res = await fetch(apiUrl(`/monitors/${id}/checks?limit=200`), { cache: "no-store" });
  return parseJson<CheckResult[]>(res);
}

export async function fetchTags(): Promise<Tag[]> {
  const res = await fetch(apiUrl("/tags"), { cache: "no-store" });
  return parseJson<Tag[]>(res);
}

export async function createTag(name: string, color?: string | null): Promise<Tag> {
  const res = await fetch(apiUrl("/tags"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, color: color ?? null }),
  });
  return parseJson<Tag>(res);
}

export async function fetchIncidents(): Promise<Incident[]> {
  const res = await fetch(apiUrl("/incidents"), { cache: "no-store" });
  return parseJson<Incident[]>(res);
}

export async function fetchIncident(id: number): Promise<IncidentDetail> {
  const res = await fetch(apiUrl(`/incidents/${id}`), { cache: "no-store" });
  return parseJson<IncidentDetail>(res);
}

export async function resolveIncident(id: number): Promise<Incident> {
  const res = await fetch(apiUrl(`/incidents/${id}/resolve`), { method: "POST" });
  return parseJson<Incident>(res);
}

export async function fetchAlerts(): Promise<AlertConfig[]> {
  const res = await fetch(apiUrl("/alerts"), { cache: "no-store" });
  return parseJson<AlertConfig[]>(res);
}

export async function createAlert(body: {
  kind: "slack" | "email";
  name?: string;
  config: Record<string, unknown>;
  enabled?: boolean;
  monitor_id?: number | null;
}): Promise<AlertConfig> {
  const res = await fetch(apiUrl("/alerts"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "default", enabled: true, ...body }),
  });
  return parseJson<AlertConfig>(res);
}

export async function deleteAlert(id: number): Promise<void> {
  const res = await fetch(apiUrl(`/alerts/${id}`), { method: "DELETE" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
}

export async function fetchPublicStatus(): Promise<PublicStatusResponse> {
  return parseJson<PublicStatusResponse>(await fetch(apiUrl("/public/status"), { cache: "no-store" }));
}
