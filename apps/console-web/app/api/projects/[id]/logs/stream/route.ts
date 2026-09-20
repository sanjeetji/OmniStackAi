import { NextRequest, NextResponse } from "next/server";
import { streamProjectLogs } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  const searchParams = request.nextUrl.searchParams;
  const source = (searchParams.get("source") as "build" | "app") || "build";

  let upstream: Response;
  try {
    upstream = await streamProjectLogs(token, id, source);
  } catch {
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("Content-Type") ?? "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
