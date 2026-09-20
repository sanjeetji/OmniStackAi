import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, getProjectUsage } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  const daysStr = request.nextUrl.searchParams.get("days") || "30";
  const days = parseInt(daysStr, 10) || 30;

  try {
    const usage = await getProjectUsage(token, id, days);
    return NextResponse.json(usage, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
