"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import type { IncidentDetail } from "@/lib/api";
import { fetchIncident, resolveIncident } from "@/lib/api";

function fmt(s: string | null | undefined) {
  if (!s) return "—";
  return new Date(s).toLocaleString();
}

function dur(sec: number | null | undefined) {
  if (sec == null) return "—";
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  return `${m}m ${sec % 60}s`;
}

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [i, setI] = useState<IncidentDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    void (async () => {
      try {
        setI(await fetchIncident(id));
        setErr(null);
      } catch (e) {
        setErr(e instanceof Error ? e.message : "load failed");
      }
    })();
  }, [id]);

  if (!Number.isFinite(id)) return <p className="text-rose-200">Invalid id</p>;
  if (err) return <p className="text-rose-200">{err}</p>;
  if (!i) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <Link className="text-sm text-accent hover:underline" href="/">
        ← Back
      </Link>
      <h1 className="text-2xl font-semibold text-white">{i.title}</h1>
      <div
        className={
          "inline-block rounded-full px-3 py-0.5 text-sm " +
          (i.status === "open"
            ? "bg-amber-500/20 text-amber-200"
            : "bg-emerald-500/20 text-emerald-200")
        }
      >
        {i.status}
      </div>

      <section className="rounded-xl border border-white/10 bg-surface-card p-5">
        <h2 className="text-sm font-medium text-slate-500">Monitor</h2>
        <p className="mt-1 text-lg text-white">
          <Link className="hover:underline" href={`/monitors/${i.monitor_id}`}>
            {i.monitor_name}
          </Link>
        </p>
        <p className="text-sm text-slate-400 break-all">{i.monitor_url}</p>
      </section>

      <section className="rounded-xl border border-white/10 bg-surface-card p-5">
        <h2 className="text-sm font-medium text-slate-500">Timeline</h2>
        <ul className="mt-2 space-y-1 text-sm text-slate-300">
          <li>Start: {fmt(i.start_time || i.started_at)}</li>
          {i.resolved_at || i.end_time ? <li>End: {fmt(i.resolved_at || i.end_time)}</li> : <li>End: (open)</li>}
          <li>Duration: {dur(i.duration_seconds)}</li>
        </ul>
      </section>

      <section className="rounded-xl border border-white/10 bg-surface-card p-5">
        <h2 className="text-sm font-medium text-slate-500">Summary</h2>
        <p className="mt-2 whitespace-pre-wrap text-slate-200">{i.summary}</p>
      </section>

      {i.status === "open" ? (
        <button
          className="rounded-md border border-white/20 bg-surface-muted px-4 py-2 text-sm text-white hover:border-accent/40"
          onClick={async () => {
            setErr(null);
            try {
              await resolveIncident(i.id);
              setI(await fetchIncident(i.id));
            } catch (e) {
              setErr(e instanceof Error ? e.message : "resolve failed");
            }
          }}
          type="button"
        >
          Mark resolved
        </button>
      ) : null}
    </div>
  );
}
