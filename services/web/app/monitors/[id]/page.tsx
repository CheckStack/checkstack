"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { CheckResult, Monitor, MonitorStats, Sla, UptimeSeries } from "@/lib/api";
import { apiUrl, fetchChecks, fetchMonitor, fetchMonitorStats, fetchSla, fetchUptime } from "@/lib/api";
import { certUrgency, certUrgencyClass, daysUntilExpiry } from "@/lib/cert";

function TlsDaysRemaining({ expiresAt }: { expiresAt: string }) {
  const d = daysUntilExpiry(expiresAt);
  if (d === null) return null;
  const text = d < 0 ? "Certificate is expired." : `${d} full day(s) remaining`;
  return <div className={certUrgencyClass(certUrgency(d))}>{text}</div>;
}

export default function MonitorDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [monitor, setMonitor] = useState<Monitor | null>(null);
  const [checks, setChecks] = useState<CheckResult[]>([]);
  const [sla24, setSla24] = useState<Sla | null>(null);
  const [sla7, setSla7] = useState<Sla | null>(null);
  const [stats, setStats] = useState<MonitorStats | null>(null);
  const [uptime, setUptime] = useState<UptimeSeries | null>(null);
  const [range, setRange] = useState<"1h" | "24h" | "7d" | "30d">("24h");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    if (!Number.isFinite(id)) return;
    try {
      const m = await fetchMonitor(id);
      setMonitor(m);
      const [c, s24, s7, st, up] = await Promise.all([
        fetchChecks(id),
        fetchSla(id, "24h"),
        fetchSla(id, "7d"),
        fetchMonitorStats(id, "24h"),
        fetchUptime(id, range),
      ]);
      setChecks(c);
      setSla24(s24);
      setSla7(s7);
      setStats(st);
      setUptime(up);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load monitor");
    }
  }, [id, range]);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    void load();
    const t = setInterval(() => void load(), 15000);
    return () => clearInterval(t);
  }, [load, id]);

  const chartData = useMemo(() => {
    const pts = uptime?.points ?? [];
    return pts.map((p) => {
      const d = new Date(p.t);
      return {
        t: d.getTime(),
        latency: p.response_time_ms ?? 0,
        up: p.ok ? 100 : 0,
        ok: p.ok,
        code: p.status_code,
      };
    });
  }, [uptime]);

  if (!Number.isFinite(id)) {
    return <div className="text-sm text-rose-200">Invalid monitor id.</div>;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link className="text-xs text-accent hover:underline" href="/">
            ← Back to overview
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-white">{monitor?.name ?? "Monitor"}</h1>
          <p className="text-sm text-slate-400">{monitor?.url ?? `ID ${id}`}</p>
          <p className="mt-1 text-xs text-slate-500">
            API:{" "}
            <code className="rounded bg-surface-muted px-1 py-0.5 text-[11px] text-slate-300">
              {apiUrl(`/monitors/${id}`)}
            </code>
          </p>
        </div>
        <button
          className="rounded-md border border-white/10 px-3 py-1.5 text-xs text-slate-200 hover:border-accent/40"
          onClick={() => void load()}
          type="button"
        >
          Refresh
        </button>
      </div>

      {error ? (
        <div className="rounded-md border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-surface-card p-4 md:col-span-3">
          <div className="text-xs uppercase tracking-wide text-slate-500">TLS certificate</div>
          {monitor?.url.toLowerCase().startsWith("https://") ? (
            <div className="mt-2 space-y-1 text-sm">
              {monitor.tls_cert_expires_at ? (
                <>
                  <div className="text-lg font-semibold text-white">
                    Expires {new Date(monitor.tls_cert_expires_at).toLocaleString()}
                  </div>
                  <TlsDaysRemaining expiresAt={monitor.tls_cert_expires_at} />
                  {monitor.tls_cert_subject ? (
                    <div className="text-xs text-slate-400">Subject: {monitor.tls_cert_subject}</div>
                  ) : null}
                  {monitor.tls_cert_checked_at ? (
                    <div className="text-xs text-slate-500">
                      Last inspected {new Date(monitor.tls_cert_checked_at).toLocaleString()}
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="text-slate-400">No certificate data yet (waiting for worker).</div>
              )}
              {monitor.tls_cert_probe_error ? (
                <div className="text-xs text-rose-200">Probe: {monitor.tls_cert_probe_error}</div>
              ) : null}
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-400">TLS inspection runs only for https:// monitors.</p>
          )}
        </div>
        <div className="rounded-xl border border-white/10 bg-surface-card p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">SLA (24h)</div>
          <div className="mt-2 text-2xl font-semibold text-white">
            {sla24 ? `${sla24.uptime_percent.toFixed(3)}%` : "—"}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {sla24 ? `${sla24.successful_checks}/${sla24.total_checks} checks` : ""}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-surface-card p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">SLA (7d)</div>
          <div className="mt-2 text-2xl font-semibold text-white">
            {sla7 ? `${sla7.uptime_percent.toFixed(3)}%` : "—"}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {sla7 ? `${sla7.successful_checks}/${sla7.total_checks} checks` : ""}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-surface-card p-4">
          <div className="text-xs uppercase tracking-wide text-slate-500">Last status</div>
          <div className="mt-2 text-2xl font-semibold text-white">{monitor?.last_status ?? "unknown"}</div>
          <div className="mt-1 text-xs text-slate-500">
            {monitor?.last_checked_at ? new Date(monitor.last_checked_at).toLocaleString() : "Not checked yet"}
          </div>
        </div>
        {stats ? (
          <div className="rounded-xl border border-white/10 bg-surface-card p-4 md:col-span-3">
            <div className="text-xs uppercase tracking-wide text-slate-500">Response time (24h)</div>
            <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4 text-sm text-slate-200">
              <div>
                <div className="text-xs text-slate-500">avg</div>
                <div className="text-lg font-semibold text-white">
                  {stats.avg_latency_ms == null ? "—" : `${Math.round(stats.avg_latency_ms)} ms`}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">p95</div>
                <div className="text-lg font-semibold text-white">
                  {stats.p95_latency_ms == null ? "—" : `${Math.round(stats.p95_latency_ms)} ms`}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">min / max</div>
                <div className="text-lg font-semibold text-white">
                  {stats.min_latency_ms == null || stats.max_latency_ms == null
                    ? "—"
                    : `${Math.round(stats.min_latency_ms)} / ${Math.round(stats.max_latency_ms)} ms`}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">with latency / checks</div>
                <div className="text-lg font-semibold text-white">
                  {stats.with_latency} / {stats.total_checks}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-white/10 bg-surface-card p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-white">Uptime &amp; response time</h2>
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-xs text-slate-500">{uptime ? `${chartData.length} points · ${range}` : ""}</div>
            {(["1h", "24h", "7d", "30d"] as const).map((k) => (
              <button
                className={
                  "rounded-md border px-2 py-1 text-xs " +
                  (range === k
                    ? "border-accent/50 bg-surface-muted text-slate-100"
                    : "border-white/10 text-slate-300 hover:border-accent/40")
                }
                key={k}
                onClick={() => setRange(k)}
                type="button"
              >
                {k}
              </button>
            ))}
          </div>
        </div>
        <div className="h-72 w-full">
          {chartData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              No samples in this window. The worker records checks on your configured interval.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData}>
                <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                <XAxis
                  dataKey="t"
                  domain={["dataMin", "dataMax"]}
                  scale="time"
                  stroke="#64748b"
                  tick={{ fontSize: 10 }}
                  type="number"
                  tickFormatter={(v: number) =>
                    new Date(v).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                  }
                />
                <YAxis
                  domain={[0, 100]}
                  stroke="#6ee7b7"
                  tick={{ fontSize: 10 }}
                  tickFormatter={() => ""}
                  width={24}
                  yAxisId="up"
                />
                <YAxis
                  dataKey="latency"
                  label={{ value: "ms", angle: -90, position: "insideLeft", style: { fill: "#94a3b8", fontSize: 11 } }}
                  stroke="#64748b"
                  tick={{ fontSize: 10 }}
                  yAxisId="lat"
                />
                <Tooltip
                  contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.08)" }}
                  formatter={(value, name) => {
                    if (name === "up") {
                      return [((value as number) === 100 ? "up" : "down") as string, "check"];
                    }
                    return [value, "latency (ms)"];
                  }}
                  labelFormatter={(l) => new Date(Number(l)).toLocaleString()}
                />
                <defs>
                  <linearGradient id="upGrad" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#6ee7b7" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#0f172a" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  dataKey="up"
                  fill="url(#upGrad)"
                  isAnimationActive={false}
                  stroke="none"
                  yAxisId="up"
                />
                <Line
                  connectNulls
                  dataKey="latency"
                  dot={false}
                  isAnimationActive={false}
                  stroke="#22d3ee"
                  strokeWidth={1.5}
                  type="monotone"
                  yAxisId="lat"
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Green area: 100% when a check succeeded, 0% on failure. Cyan: response time.
        </p>
      </section>

      <section className="rounded-xl border border-white/10">
        <div className="border-b border-white/5 px-4 py-3 text-sm font-semibold text-white">Recent checks</div>
        <div className="max-h-80 overflow-auto">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-surface-muted/60 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Time</th>
                <th className="px-4 py-2">OK</th>
                <th className="px-4 py-2">Code</th>
                <th className="px-4 py-2">Latency</th>
                <th className="px-4 py-2">Error</th>
              </tr>
            </thead>
            <tbody>
              {checks.map((c) => (
                <tr className="border-t border-white/5" key={c.id}>
                  <td className="px-4 py-2 text-xs text-slate-300">{new Date(c.checked_at).toLocaleString()}</td>
                  <td className="px-4 py-2">{c.ok ? <span className="text-emerald-300">yes</span> : "no"}</td>
                  <td className="px-4 py-2 text-slate-300">{c.status_code ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-300">{c.latency_ms ?? "—"}</td>
                  <td className="px-4 py-2 text-xs text-rose-200">{c.error_message ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
