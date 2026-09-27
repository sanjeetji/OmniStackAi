import { NextRequest, NextResponse } from "next/server";
import { controlPlaneUrl } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

/** PC-011: forward a console request to the control plane under the caller's session. The
 * control plane decides everything (roles, plans, ownership); this only carries the request. */
export async function passThrough(request: NextRequest, prefix: string, segments: string[]): Promise<Response> {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const path = segments.map(encodeURIComponent).join("/");
  const search = request.nextUrl.search;
  const init: RequestInit = {
    method: request.method,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    cache: "no-store",
  };
  if (request.method !== "GET" && request.method !== "HEAD") init.body = await request.text();
  try {
    const upstream = await fetch(`${controlPlaneUrl()}/${prefix}${path ? `/${path}` : ""}${search}`, init);
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
