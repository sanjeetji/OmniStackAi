import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  inviteWorkspaceMember,
  listWorkspaceInvites,
  type InviteMemberRequest,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  try {
    const data = await listWorkspaceInvites(token, id);
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  let body: InviteMemberRequest;
  try {
    body = (await request.json()) as InviteMemberRequest;
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  if (!body.email || !body.email.trim()) {
    return NextResponse.json({ error: "email is required" }, { status: 400 });
  }

  try {
    const invite = await inviteWorkspaceMember(token, id, {
      email: body.email.trim(),
      role: body.role || "member",
    });
    return NextResponse.json(invite, { status: 201 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
