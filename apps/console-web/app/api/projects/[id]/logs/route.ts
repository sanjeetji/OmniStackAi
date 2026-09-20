import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  clearProjectLogs,
  getProjectLogs,
} from "@/lib/control-plane";
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
  const searchParams = request.nextUrl.searchParams;
  const source = (searchParams.get("source") as "build" | "app") || "build";
  const sinceStr = searchParams.get("since");
  const since = sinceStr ? parseInt(sinceStr, 10) : undefined;
  const limitStr = searchParams.get("limit");
  const limit = limitStr ? parseInt(limitStr, 10) : undefined;

  try {
    const logs = await getProjectLogs(token, id, source, since, limit);
    return NextResponse.json(logs, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  const searchParams = request.nextUrl.searchParams;
  const source = (searchParams.get("source") as "build" | "app") || undefined;

  try {
    const result = await clearProjectLogs(token, id, source);
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
