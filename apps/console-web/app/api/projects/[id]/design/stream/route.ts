import { NextRequest, NextResponse } from "next/server";
import { streamProjectDesign } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-098: the model designs the pages after the build. Only a clean list of page paths is forwarded.
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const body = (await request.json().catch(() => ({}))) as { pages?: unknown };
  const pages = Array.isArray(body.pages)
    ? body.pages.filter((p): p is string => typeof p === "string" && p.length > 0 && p.length < 300)
    : undefined;
  const { id } = await params;
  let upstream: Response;
  try {
    upstream = await streamProjectDesign(token, id, pages);
  } catch {
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
