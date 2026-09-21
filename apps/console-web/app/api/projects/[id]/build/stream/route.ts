import { NextRequest, NextResponse } from "next/server";
import { streamProjectBuild } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

interface BuildStreamRequestBody {
  prompt?: unknown;
  mention_skills?: unknown;
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
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

  // @skill mentions (F-04) were parsed by the Studio but dropped here, so they never reached the
  // control-plane (R-518). Forward only a clean list of skill names.
  const mentionSkills = Array.isArray(body.mention_skills)
    ? body.mention_skills.filter((name): name is string => typeof name === "string" && name.length > 0)
    : [];

  const { id } = await params;
  let upstream: Response;
  try {
    upstream = await streamProjectBuild(token, id, body.prompt, mentionSkills);
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
