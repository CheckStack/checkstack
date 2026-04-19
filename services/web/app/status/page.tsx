"use client";

import { useEffect, useState } from "react";

import type { PublicStatusResponse } from "@/lib/api";
import { fetchPublicStatus } from "@/lib/api";

export default function PublicStatusPage() {
  const [data, setData] = useState<PublicStatusResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setData(await fetchPublicStatus());
        setErr(null);
      } catch (e) {
        setErr(e instanceof Error ? e.message : "failed to load");
      }
    })();
  }, []);

  if (err) {
    return <p className="text-rose-300">Could not load status. {err}</p>;
  }
  if (!data) {
    return <p className="text-slate-500">Loading…</p>;
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8 text-center">
      <h1 className="text-3xl font-bold text-white">Service status</h1>
      <p className="text-sm text-slate-500">CheckStack public status (no sign-in)</p>
      <div className="space-y-3 text-left">
        {data.monitors.length === 0 ? <p className="text-slate-400">No monitors configured yet.</p> : null}
        {data.monitors.map((m) => (
          <div
            className="flex items-center justify-between rounded-xl border border-white/10 bg-surface-card px-5 py-4"
            key={m.id}
          >
            <div>
              <div className="font-medium text-white">{m.name}</div>
              <div className="text-xs text-slate-500">{m.url}</div>
            </div>
            <div className="text-right text-sm">
              <div
                className={
                  m.status === "up" ? "font-semibold text-emerald-300" : "font-semibold text-amber-200"
                }
              >
                {m.status}
              </div>
              <div className="text-slate-400">SLA 24h: {m.sla_24h_percent.toFixed(1)}%</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
