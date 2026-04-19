"use client";

import { useCallback, useEffect, useState } from "react";

import type { AlertConfig } from "@/lib/api";
import { createAlert, deleteAlert, fetchAlerts } from "@/lib/api";

export default function AlertsPage() {
  const [items, setItems] = useState<AlertConfig[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [slackUrl, setSlackUrl] = useState("");
  const [emailTo, setEmailTo] = useState("");

  const load = useCallback(async () => {
    setErr(null);
    setItems(await fetchAlerts());
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Alert channels</h1>
        <p className="mt-1 text-sm text-slate-400">
          Configure Slack webhooks and email recipients. SMTP is set via <code className="text-slate-300">SMTP_*</code>{" "}
          environment variables on the API. Incidents from monitors with alerts enabled and matching these routes will
          notify.
        </p>
      </div>

      {err ? <div className="rounded border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">{err}</div> : null}

      <div className="space-y-4 rounded-xl border border-white/10 bg-surface-card p-6">
        <h2 className="text-sm font-semibold text-white">Add Slack</h2>
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setErr(null);
            try {
              await createAlert({ kind: "slack", name: "slack", config: { webhook_url: slackUrl }, enabled: true });
              setSlackUrl("");
              await load();
            } catch (ex) {
              setErr(ex instanceof Error ? ex.message : "failed");
            }
          }}
        >
          <label className="block text-xs text-slate-500">Incoming webhook URL</label>
          <input
            className="w-full rounded-md border border-white/10 bg-surface-muted px-3 py-2 text-sm text-slate-100"
            onChange={(e) => setSlackUrl(e.target.value)}
            placeholder="https://hooks.slack.com/services/..."
            required
            value={slackUrl}
          />
          <button
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-slate-950"
            type="submit"
            disabled={!slackUrl}
          >
            Add Slack
          </button>
        </form>
      </div>

      <div className="space-y-4 rounded-xl border border-white/10 bg-surface-card p-6">
        <h2 className="text-sm font-semibold text-white">Add email</h2>
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            setErr(null);
            try {
              await createAlert({ kind: "email", name: "email", config: { to: emailTo }, enabled: true });
              setEmailTo("");
              await load();
            } catch (ex) {
              setErr(ex instanceof Error ? ex.message : "failed");
            }
          }}
        >
          <label className="block text-xs text-slate-500">To address</label>
          <input
            className="w-full rounded-md border border-white/10 bg-surface-muted px-3 py-2 text-sm text-slate-100"
            onChange={(e) => setEmailTo(e.target.value)}
            placeholder="oncall@example.com"
            required
            type="email"
            value={emailTo}
          />
          <button
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-slate-950"
            type="submit"
            disabled={!emailTo}
          >
            Add email
          </button>
        </form>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-slate-300">Configured</h2>
        <ul className="mt-2 space-y-2">
          {items.length === 0 ? <li className="text-sm text-slate-500">No channels yet.</li> : null}
          {items.map((a) => (
            <li
              className="flex items-center justify-between rounded-lg border border-white/10 bg-surface-card px-4 py-2 text-sm"
              key={a.id}
            >
              <div>
                <div className="font-medium text-white">
                  {a.kind} <span className="text-slate-500">· {a.name}</span>{" "}
                  <span
                    className={a.enabled ? "text-emerald-300" : "text-amber-300"}
                  >{a.enabled ? "on" : "off"}</span>
                </div>
                <div className="text-xs text-slate-500">
                  {a.kind === "slack" ? (a.config.webhook_url as string)?.slice(0, 64) : String(a.config.to)}…
                </div>
              </div>
              <button
                className="text-xs text-rose-300 hover:underline"
                onClick={async () => {
                  if (!confirm("Remove this channel?")) return;
                  setErr(null);
                  try {
                    await deleteAlert(a.id);
                    await load();
                  } catch (ex) {
                    setErr(ex instanceof Error ? ex.message : "delete failed");
                  }
                }}
                type="button"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
