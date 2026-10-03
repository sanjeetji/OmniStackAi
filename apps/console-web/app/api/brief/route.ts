import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, proposeBrief } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-128: the project brief for a prompt - apps, features, questions, brand, region and stack, every
// answer pre-filled. `locale` and `timezone` are the person's own browser settings (smart defaults).
export async function POST(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const body = (await request.json().catch(() => ({}))) as { prompt?: unknown; locale?: unknown; timezone?: unknown };
  const prompt = typeof body.prompt === "string" ? body.prompt.trim() : "";
  if (!prompt) return NextResponse.json({ error: "prompt is required" }, { status: 400 });
  const text = (value: unknown, max: number) => (typeof value === "string" ? value.slice(0, max) : undefined);
  try {
    return NextResponse.json(await proposeBrief(token, prompt, text(body.locale, 20), text(body.timezone, 60)), { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
