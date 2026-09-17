import { NextRequest, NextResponse } from "next/server";
import { buildApp, ControlPlaneError } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

interface BuildRequestBody {
  prompt?: unknown;
}

export async function POST(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  let body: BuildRequestBody;
  try {
    body = (await request.json()) as BuildRequestBody;
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  if (typeof body.prompt !== "string" || body.prompt.trim().length === 0) {
    return NextResponse.json({ error: "prompt is required" }, { status: 400 });
  }

  try {
    const result = await buildApp(token, body.prompt);
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
