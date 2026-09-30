import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, actOnProjectStores, type StoreAction, type StorePlatform } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// R-574: POST {platform: android | ios, action: check | build | submit} for the project's mobile app.
// The store credentials are the project's secrets; the control plane adds them, and they never
// come back in the reply.
const PLATFORMS: StorePlatform[] = ["android", "ios"];
const ACTIONS: StoreAction[] = ["check", "build", "submit"];

export const maxDuration = 960;

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const { id } = await params;
  const body = (await request.json().catch(() => ({}))) as { platform?: string; action?: string };
  if (!(PLATFORMS as string[]).includes(body.platform ?? "")) {
    return NextResponse.json({ error: "platform must be android or ios" }, { status: 400 });
  }
  const action = (ACTIONS as string[]).includes(body.action ?? "") ? (body.action as StoreAction) : "check";
  try {
    return NextResponse.json(await actOnProjectStores(token, id, body.platform as StorePlatform, action));
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
