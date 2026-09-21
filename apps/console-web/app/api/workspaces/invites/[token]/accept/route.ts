import { NextRequest, NextResponse } from "next/server";
import {
  acceptWorkspaceInvite,
  ControlPlaneError,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ token: string }> },
) {
  const sessionToken = await getSessionToken();
  if (!sessionToken) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { token } = await params;
  try {
    const res = await acceptWorkspaceInvite(sessionToken, token);
    return NextResponse.json(res, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
