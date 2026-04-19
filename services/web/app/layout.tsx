import type { Metadata } from "next";
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
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <div>
              <div className="text-sm font-semibold tracking-wide text-accent">CheckStack</div>
              <div className="text-xs text-slate-400">Uptime · SLA · Incidents</div>
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
