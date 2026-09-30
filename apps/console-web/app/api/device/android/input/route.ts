import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, sendAndroidInput, type AndroidInput } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-063: a tap, swipe, text or key for the emulator. The Studio validates every field again.
export async function POST(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const body = (await request.json().catch(() => null)) as AndroidInput | null;
  if (!body || !["tap", "swipe", "text", "key"].includes(body.kind)) {
    return NextResponse.json({ error: "kind must be tap, swipe, text or key" }, { status: 400 });
  }
  try {
    return NextResponse.json(await sendAndroidInput(token, body));
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
