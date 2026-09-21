import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  getProjectAnalyticsReport,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  const rangeParam = request.nextUrl.searchParams.get("range") ?? "7d";
  const range =
    rangeParam === "24h" || rangeParam === "7d" || rangeParam === "30d"
      ? rangeParam
      : "7d";

  try {
    const data = await getProjectAnalyticsReport(token, id, range);
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}
