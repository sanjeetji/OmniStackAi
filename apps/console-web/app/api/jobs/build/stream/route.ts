import { NextRequest, NextResponse } from "next/server";
import { streamBuildApp } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

interface BuildStreamRequestBody {
  prompt?: unknown;
}

export async function POST(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  let body: BuildStreamRequestBody;
  try {
    body = (await request.json()) as BuildStreamRequestBody;
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  if (typeof body.prompt !== "string" || body.prompt.trim().length === 0) {
    return NextResponse.json({ error: "prompt is required" }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await streamBuildApp(token, body.prompt);
  } catch {
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }

  // Relay the upstream response through unchanged. Both real shapes the control-plane can return
  // round-trip correctly through this same pipe-through: a streamed `text/event-stream` success
  // body, and a plain buffered `application/json` pre-stream rejection (Solution Pack/Ecosystem/
  // hybrid_ui, a normal 400) - neither this route nor the browser needs to branch on which one it
  // got.
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
