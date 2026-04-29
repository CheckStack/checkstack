"use client";

import { useState } from "react";
import { login, register } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<"login" | "register" | null>(null);
  const router = useRouter();

  async function doLogin() {
    const out = await login(email.trim(), password);
    setToken(out.access_token);
    router.push("/");
  }

  return (
    <div className="max-w-md space-y-4">
      <h1 className="text-2xl text-white font-semibold">Sign in</h1>
      {err ? <div className="text-rose-300 text-sm">{err}</div> : null}
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setErr(null);
          setBusy("login");
          try {
            await doLogin();
          } catch (e) {
            setErr(e instanceof Error ? e.message : "Login failed");
          } finally {
            setBusy(null);
          }
        }}
      >
        <input
          className="w-full p-2 rounded bg-surface-muted border border-white/10"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          type="email"
          required
        />
        <input
          className="w-full p-2 rounded bg-surface-muted border border-white/10"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          placeholder="Password"
          required
          minLength={6}
        />
        <div className="flex gap-2">
          <button disabled={busy !== null} className="bg-accent text-slate-900 rounded px-3 py-2" type="submit">
            {busy === "login" ? "Signing in..." : "Login"}
          </button>
          <button
            type="button"
            disabled={busy !== null}
            className="border border-white/20 rounded px-3 py-2 text-slate-200"
            onClick={async () => {
              setErr(null);
              setBusy("register");
              try {
                await register(email.trim(), password);
                await doLogin();
              } catch (e) {
                setErr(e instanceof Error ? e.message : "Register failed");
              } finally {
                setBusy(null);
              }
            }}
          >
            {busy === "register" ? "Registering..." : "Register"}
          </button>
        </div>
      </form>
    </div>
  );
}
