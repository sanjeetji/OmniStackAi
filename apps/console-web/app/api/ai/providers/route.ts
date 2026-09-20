import { NextResponse } from "next/server";
import { ControlPlaneError, getAIProviders } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET() {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  try {
    const data = await getAIProviders(token);
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
