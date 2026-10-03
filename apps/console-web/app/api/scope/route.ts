import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, proposeScope } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-127: what will be built for a prompt - one app, an app and its admin, a few apps or an
// ecosystem - each app with its reason. `included` re-plans with apps switched on or off.
export async function POST(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const body = (await request.json().catch(() => ({}))) as { prompt?: unknown; included?: unknown };
  const prompt = typeof body.prompt === "string" ? body.prompt.trim() : "";
  if (!prompt) return NextResponse.json({ error: "prompt is required" }, { status: 400 });
  const included =
    body.included && typeof body.included === "object"
      ? Object.fromEntries(Object.entries(body.included as Record<string, unknown>).map(([k, v]) => [k, Boolean(v)]))
      : undefined;
  try {
    return NextResponse.json(await proposeScope(token, prompt, included), { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
