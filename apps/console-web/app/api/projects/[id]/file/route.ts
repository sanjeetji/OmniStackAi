import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, getProjectFile } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const path = searchParams.get("path");
  if (!path) {
    return NextResponse.json({ error: "path query parameter is required" }, { status: 400 });
  }

  const { id } = await params;
  try {
    const file = await getProjectFile(token, id, path);
    return NextResponse.json(file, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
