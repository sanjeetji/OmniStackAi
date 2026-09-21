import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  removeWorkspaceMember,
  updateWorkspaceMemberRole,
  type WorkspaceRole,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; userId: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, userId } = await params;
  let body: { role: WorkspaceRole };
  try {
    body = (await request.json()) as { role: WorkspaceRole };
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  if (!body.role) {
    return NextResponse.json({ error: "role is required" }, { status: 400 });
  }

  try {
    const updated = await updateWorkspaceMemberRole(token, id, userId, body.role);
    return NextResponse.json(updated, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; userId: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, userId } = await params;
  try {
    const res = await removeWorkspaceMember(token, id, userId);
    return NextResponse.json(res, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
