"use client";

import { useState } from "react";
import { login, register } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const router = useRouter();

  return <div className="max-w-md space-y-4">
    <h1 className="text-2xl text-white font-semibold">Sign in</h1>
    {err ? <div className="text-rose-300 text-sm">{err}</div> : null}
    <form className="space-y-3" onSubmit={async (e) => {
      e.preventDefault();
      try {
        const out = await login(email, password);
        setToken(out.access_token);
        router.push('/');
      } catch (e) { setErr(e instanceof Error ? e.message : 'failed'); }
    }}>
      <input className="w-full p-2 rounded bg-surface-muted border border-white/10" value={email} onChange={(e)=>setEmail(e.target.value)} placeholder="Email" />
      <input className="w-full p-2 rounded bg-surface-muted border border-white/10" value={password} onChange={(e)=>setPassword(e.target.value)} type="password" placeholder="Password" />
      <div className="flex gap-2">
        <button className="bg-accent text-slate-900 rounded px-3 py-2">Login</button>
        <button type="button" className="border border-white/20 rounded px-3 py-2 text-slate-200" onClick={async()=>{ await register(email,password); const out=await login(email,password); setToken(out.access_token); router.push('/'); }}>Register</button>
      </div>
    </form>
  </div>;
}
