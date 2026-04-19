import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "CheckStack",
  description: "Uptime, SLA, and incident insights for Kubernetes teams.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <div className="border-b border-white/10 bg-surface-muted/60 backdrop-blur">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
            <div className="flex flex-1 items-center gap-6">
              <div>
                <div className="text-sm font-semibold tracking-wide text-accent">CheckStack</div>
                <div className="text-xs text-slate-400">Uptime · SLA · Incidents</div>
              </div>
              <nav className="flex items-center gap-1 text-xs">
                <Link className="rounded-md px-2 py-1 text-slate-300 hover:bg-white/5 hover:text-white" href="/">
                  Overview
                </Link>
                <Link className="rounded-md px-2 py-1 text-slate-300 hover:bg-white/5 hover:text-white" href="/alerts">
                  Alerts
                </Link>
                <Link
                  className="rounded-md px-2 py-1 text-slate-300 hover:bg-white/5 hover:text-white"
                  href="/status"
                >
                  Status
                </Link>
              </nav>
            </div>
            <a
              className="rounded-md border border-white/10 px-3 py-1.5 text-xs text-slate-200 hover:border-accent/40 hover:text-white"
              href="https://github.com/CheckStack/checkstack"
              rel="noreferrer"
              target="_blank"
            >
              GitHub
            </a>
          </div>
        </div>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
