"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import type { Incident, Monitor, Sla } from "@/lib/api";
import { certUrgency, certUrgencyClass, daysUntilExpiry } from "@/lib/cert";
import {
  createMonitor,
  deleteMonitor,
  fetchIncidents,
  fetchMonitors,
  fetchSla,
  resolveIncident,
} from "@/lib/api";

type Row = { monitor: Monitor; sla24: Sla | null };

export default function HomePage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [url, setUrl] = useState("https://");
  const [intervalSeconds, setIntervalSeconds] = useState(60);

  const openIncidents = useMemo(() => incidents.filter((i) => i.status === "open").length, [incidents]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [mons, incs] = await Promise.all([fetchMonitors(), fetchIncidents()]);
      const slaPairs = await Promise.all(
        mons.map(async (m) => {
          try {
            const sla24 = await fetchSla(m.id, "24h");
            return { monitor: m, sla24 };
          } catch {
            return { monitor: m, sla24: null };
          }
        }),
      );
      setRows(slaPairs);
      setIncidents(incs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    const t = setInterval(() => void refresh(), 15000);
    return () => clearInterval(t);
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createMonitor({
        name,
        url,
        interval_seconds: intervalSeconds,
        timeout_seconds: 10,
        failure_threshold: 3,
      });
      setName("");
      setUrl("https://");
      setIntervalSeconds(60);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  async function onDelete(id: number) {
    setError(null);
    try {
      await deleteMonitor(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-white">Overview</h1>
        <p className="max-w-2xl text-sm text-slate-400">
          Add HTTP or HTTPS endpoints, watch live status, track 24-hour SLA, and see TLS certificate expiry for HTTPS
          URLs. Incidents open automatically after repeated failures.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <Stat label="Monitors" value={String(rows.length)} hint="Configured endpoints" />
        <Stat label="Open incidents" value={String(openIncidents)} hint="Needs attention" />
        <Stat label="Refresh" value="15s" hint="Dashboard polling" />
      </section>

      <section className="rounded-xl border border-white/10 bg-surface-card p-6 shadow-lg shadow-black/30">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Add monitor</h2>
            <p className="text-xs text-slate-400">Defaults: 10s timeout, 3 consecutive failures to open an incident.</p>
          </div>
        </div>
        <form className="grid gap-3 md:grid-cols-4" onSubmit={onCreate}>
          <label className="space-y-1 text-sm text-slate-300 md:col-span-1">
            <span className="text-xs uppercase tracking-wide text-slate-500">Name</span>
            <input
              className="w-full rounded-md border border-white/10 bg-surface-muted px-3 py-2 text-sm outline-none ring-accent/30 focus:ring"
              onChange={(e) => setName(e.target.value)}
              required
              value={name}
            />
          </label>
          <label className="space-y-1 text-sm text-slate-300 md:col-span-2">
            <span className="text-xs uppercase tracking-wide text-slate-500">URL</span>
            <input
              className="w-full rounded-md border border-white/10 bg-surface-muted px-3 py-2 text-sm outline-none ring-accent/30 focus:ring"
              onChange={(e) => setUrl(e.target.value)}
              required
              type="url"
              value={url}
            />
          </label>
          <label className="space-y-1 text-sm text-slate-300">
            <span className="text-xs uppercase tracking-wide text-slate-500">Interval (s)</span>
            <input
              className="w-full rounded-md border border-white/10 bg-surface-muted px-3 py-2 text-sm outline-none ring-accent/30 focus:ring"
              min={10}
              onChange={(e) => setIntervalSeconds(Number(e.target.value))}
              type="number"
              value={intervalSeconds}
            />
          </label>
          <div className="md:col-span-4 flex justify-end">
            <button
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-accent-dim"
              type="submit"
            >
              Save monitor
            </button>
          </div>
        </form>
      </section>

      {error ? (
        <div className="rounded-md border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      <section className="space-y-3">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Monitors</h2>
            <p className="text-xs text-slate-500">{loading ? "Loading…" : "Live from the CheckStack API"}</p>
          </div>
          <button
            className="rounded-md border border-white/10 px-3 py-1.5 text-xs text-slate-200 hover:border-accent/40"
            onClick={() => void refresh()}
            type="button"
          >
            Refresh now
          </button>
        </div>

        <div className="overflow-hidden rounded-xl border border-white/10">
          <table className="w-full border-collapse text-sm">
            <thead className="bg-surface-muted/80 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">SLA (24h)</th>
                <th className="px-4 py-3">TLS expiry</th>
                <th className="px-4 py-3">Failures</th>
                <th className="px-4 py-3">Last check</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-slate-400" colSpan={7}>
                    No monitors yet. Add one above to start collecting uptime.
                  </td>
                </tr>
              ) : (
                rows.map(({ monitor, sla24 }) => (
                  <tr className="border-t border-white/5 bg-surface-card/40 hover:bg-surface-card/80" key={monitor.id}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-white">{monitor.name}</div>
                      <div className="text-xs text-slate-500">{monitor.url}</div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={monitor.last_status} />
                    </td>
                    <td className="px-4 py-3 text-slate-200">
                      {sla24 ? `${sla24.uptime_percent.toFixed(2)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <CertExpirySummary monitor={monitor} />
                    </td>
                    <td className="px-4 py-3 text-slate-200">{monitor.consecutive_failures}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {monitor.last_checked_at ? new Date(monitor.last_checked_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <Link
                          className="rounded-md border border-white/10 px-2 py-1 text-xs text-slate-200 hover:border-accent/40"
                          href={`/monitors/${monitor.id}`}
                        >
                          Details
                        </Link>
                        <button
                          className="rounded-md border border-rose-500/30 px-2 py-1 text-xs text-rose-200 hover:border-rose-400"
                          onClick={() => void onDelete(monitor.id)}
                          type="button"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Recent incidents</h2>
        <div className="space-y-3">
          {incidents.length === 0 ? (
            <div className="rounded-xl border border-white/10 bg-surface-card px-4 py-6 text-sm text-slate-400">
              No incidents yet. When a monitor crosses the failure threshold, CheckStack opens one automatically.
            </div>
          ) : (
            incidents.slice(0, 8).map((inc) => (
              <article
                className="rounded-xl border border-white/10 bg-surface-card px-4 py-4 shadow-inner shadow-black/20"
                key={inc.id}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-semibold text-white">{inc.title}</div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        inc.status === "open"
                          ? "bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/30"
                          : "bg-emerald-500/10 text-emerald-200 ring-1 ring-emerald-500/20"
                      }`}
                    >
                      {inc.status}
                    </span>
                    {inc.status === "open" ? (
                      <button
                        className="rounded-md border border-white/10 px-2 py-1 text-xs text-slate-200 hover:border-accent/40"
                        onClick={async () => {
                          await resolveIncident(inc.id);
                          await refresh();
                        }}
                        type="button"
                      >
                        Resolve
                      </button>
                    ) : null}
                  </div>
                </div>
                <p className="mt-2 text-sm text-slate-300">{inc.summary}</p>
                <p className="mt-2 text-xs text-slate-500">
                  Started {new Date(inc.started_at).toLocaleString()}
                  {inc.resolved_at ? ` · Resolved ${new Date(inc.resolved_at).toLocaleString()}` : ""}
                </p>
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-surface-card p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{hint}</div>
    </div>
  );
}

function StatusPill({ status }: { status: string | null }) {
  if (status === "up") {
    return <span className="text-emerald-300">● Up</span>;
  }
  if (status === "down") {
    return <span className="text-rose-300">● Down</span>;
  }
  return <span className="text-slate-500">● Unknown</span>;
}

function CertExpirySummary({ monitor }: { monitor: Monitor }) {
  if (!monitor.url.toLowerCase().startsWith("https://")) {
    return <span className="text-slate-500">n/a</span>;
  }
  if (!monitor.tls_cert_expires_at && monitor.tls_cert_probe_error) {
    return (
      <span className="text-rose-300" title={monitor.tls_cert_probe_error}>
        error
      </span>
    );
  }
  if (!monitor.tls_cert_expires_at) {
    return <span className="text-slate-500">…</span>;
  }
  const days = daysUntilExpiry(monitor.tls_cert_expires_at);
  const u = certUrgency(days);
  const line1 = new Date(monitor.tls_cert_expires_at).toLocaleDateString();
  const line2 = days === null ? "" : days < 0 ? "expired" : `${days}d left`;
  return (
    <div className="space-y-0.5">
      <div className="flex items-center gap-1 font-medium text-slate-100">
        {line1}
        {monitor.tls_cert_probe_error ? (
          <span className="text-amber-300" title={monitor.tls_cert_probe_error}>
            !
          </span>
        ) : null}
      </div>
      {line2 ? <div className={certUrgencyClass(u)}>{line2}</div> : null}
    </div>
  );
}
