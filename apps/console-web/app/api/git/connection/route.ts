import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, disconnectGit } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function DELETE(_request: NextRequest) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  try {
    const res = await disconnectGit(token);
    return NextResponse.json(res, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
