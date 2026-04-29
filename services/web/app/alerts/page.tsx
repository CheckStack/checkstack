"use client";

import { useCallback, useEffect, useState } from "react";
import { createAlertChannel, createAlertRule, fetchAlertChannels, fetchMonitors, type AlertChannel, type Monitor } from "@/lib/api";

export default function AlertsPage() {
  const [channels, setChannels] = useState<AlertChannel[]>([]);
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [type, setType] = useState<"slack" | "email" | "webhook">("slack");
  const [target, setTarget] = useState("");

  const load = useCallback(async () => {
    setErr(null);
    const [chs, mons] = await Promise.all([fetchAlertChannels(), fetchMonitors()]);
    setChannels(chs);
    setMonitors(mons);
  }, []);

  useEffect(() => { void load(); }, [load]);

  return <div className="space-y-6">
    <h1 className="text-2xl font-semibold text-white">Alerts</h1>
    {err ? <div className="text-rose-300 text-sm">{err}</div> : null}
    <form className="space-y-2" onSubmit={async (e) => {
      e.preventDefault();
      try {
        const config = type === "email" ? { to: target } : (type === "webhook" ? { url: target } : { webhook_url: target });
        await createAlertChannel({ type, config, is_active: true });
        setTarget("");
        await load();
      } catch (ex) { setErr(ex instanceof Error ? ex.message : "failed"); }
    }}>
      <select value={type} onChange={(e) => setType(e.target.value as any)} className="bg-surface-muted border border-white/10 p-2 rounded">
        <option value="slack">Slack</option><option value="email">Email</option><option value="webhook">Webhook</option>
      </select>
      <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Destination" className="ml-2 bg-surface-muted border border-white/10 p-2 rounded" />
      <button className="ml-2 rounded bg-accent px-3 py-2 text-slate-900">Add channel</button>
    </form>

    <ul className="space-y-2">{channels.map((c) => <li key={c.id} className="text-sm text-slate-200">#{c.id} {c.type}</li>)}</ul>

    <h2 className="text-lg text-white">Quick rule setup (DOWN alerts)</h2>
    <div className="space-y-2">{channels.map((c) => (
      <div key={c.id} className="flex gap-2 items-center">
        <span className="text-slate-300 text-sm">Channel #{c.id} {c.type}</span>
        <select className="bg-surface-muted border border-white/10 p-1 rounded" onChange={async (e) => {
          if (!e.target.value) return;
          await createAlertRule({ channel_id: c.id, monitor_id: Number(e.target.value), trigger_type: "DOWN", is_active: true });
          alert("Rule created");
        }}>
          <option value="">Attach to monitor...</option>
          {monitors.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
      </div>
    ))}</div>
  </div>;
}
