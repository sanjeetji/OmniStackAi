import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, actOnAndroid, getAndroidStatus } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-063: the Android emulator on this machine. GET is its state; POST {action: setup | boot | stop}
// starts that in the background (the panel polls GET).
const ACTIONS = ["setup", "boot", "stop"] as const;

export async function GET() {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  try {
    return NextResponse.json(await getAndroidStatus(token));
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const body = (await request.json().catch(() => ({}))) as { action?: string };
  const action = ACTIONS.find((a) => a === body.action);
  if (!action) return NextResponse.json({ error: "action must be setup, boot or stop" }, { status: 400 });
  try {
    return NextResponse.json(await actOnAndroid(token, action));
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
