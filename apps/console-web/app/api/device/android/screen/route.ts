import { NextResponse } from "next/server";
import { fetchAndroidScreen } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-063: the emulator's current screen (PNG), refreshed by the device panel.
export async function GET() {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  try {
    const upstream = await fetchAndroidScreen(token);
    if (!upstream.ok) {
      const text = await upstream.text();
      let message = "the emulator has no screen yet";
      try {
        message = (JSON.parse(text) as { error?: string }).error ?? message;
      } catch {
        // not JSON: keep the default message
      }
      return NextResponse.json({ error: message }, { status: upstream.status });
    }
    return new NextResponse(await upstream.arrayBuffer(), {
      headers: { "Content-Type": "image/png", "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
