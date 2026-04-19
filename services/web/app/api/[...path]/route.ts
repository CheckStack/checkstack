import { NextRequest, NextResponse } from "next/server";

const hopByHop = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
]);

function backendBase(): string {
  return (process.env.INTERNAL_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
}

function buildTarget(path: string[] | undefined, search: string): string {
  const tail = path?.length ? path.join("/") : "";
  const base = backendBase();
  return tail ? `${base}/${tail}${search}` : `${base}/${search}`;
}

async function proxy(request: NextRequest, path: string[] | undefined): Promise<NextResponse> {
  const target = buildTarget(path, request.nextUrl.search);
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === "host" || lower === "connection") {
      return;
    }
    headers.set(key, value);
  });

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const res = await fetch(target, init);
  const out = new Headers();
  res.headers.forEach((value, key) => {
    if (hopByHop.has(key.toLowerCase())) {
      return;
    }
    out.set(key, value);
  });

  return new NextResponse(res.body, { status: res.status, headers: out });
}

type Ctx = { params: Promise<{ path?: string[] }> };

export async function GET(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function PATCH(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}
