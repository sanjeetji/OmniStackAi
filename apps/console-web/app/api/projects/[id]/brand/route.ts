import { NextRequest, NextResponse } from "next/server";
import { controlPlaneUrl } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-020: read or change a project's brand (name, colours, fonts, corners, style, logo).
async function forward(request: NextRequest, id: string, method: "GET" | "POST") {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const body = method === "POST" ? await request.text() : undefined;
  if (body && body.length > 1024 * 1024) {
    return NextResponse.json({ error: "the logo may be at most 512 KB" }, { status: 413 });
  }
  try {
    const upstream = await fetch(`${controlPlaneUrl()}/projects/${encodeURIComponent(id)}/brand`, {
      method,
      headers: { Authorization: `Bearer ${token}`, ...(body ? { "Content-Type": "application/json" } : {}) },
      body,
      cache: "no-store",
    });
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  return forward(request, (await params).id, "GET");
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  return forward(request, (await params).id, "POST");
}
