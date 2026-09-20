import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  getProjectDBTableRows,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; table: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, table } = await params;
  const searchParams = request.nextUrl.searchParams;
  const schema = searchParams.get("schema") || undefined;
  const limitStr = searchParams.get("limit");
  const limit = limitStr ? parseInt(limitStr, 10) : undefined;
  const offsetStr = searchParams.get("offset");
  const offset = offsetStr ? parseInt(offsetStr, 10) : undefined;
  const orderBy = searchParams.get("order_by") || undefined;
  const directionParam = searchParams.get("direction")?.toUpperCase();
  const direction = directionParam === "DESC" ? "DESC" : directionParam === "ASC" ? "ASC" : undefined;

  try {
    const data = await getProjectDBTableRows(token, id, table, {
      schema,
      limit,
      offset,
      orderBy,
      direction,
    });
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
