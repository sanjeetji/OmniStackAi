import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, openProjectOnAndroid } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-063: open the project's running mobile preview in Expo Go on the emulator. The first time,
// Expo Go is downloaded and installed, which can take a few minutes.
export const maxDuration = 420;

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const { id } = await params;
  const body = (await request.json().catch(() => ({}))) as { app?: string };
  try {
    return NextResponse.json(await openProjectOnAndroid(token, id, typeof body.app === "string" ? body.app : undefined));
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
