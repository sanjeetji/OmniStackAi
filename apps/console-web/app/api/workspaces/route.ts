import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  createWorkspace,
  listWorkspaces,
  type CreateWorkspaceRequest,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET() {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  try {
    const data = await listWorkspaces(token);
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  let body: CreateWorkspaceRequest;
  try {
    body = (await request.json()) as CreateWorkspaceRequest;
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  if (typeof body.name !== "string" || body.name.trim().length === 0) {
    return NextResponse.json({ error: "name is required" }, { status: 400 });
  }

  try {
    const workspace = await createWorkspace(token, {
      name: body.name.trim(),
      slug: body.slug?.trim(),
      organization_id: body.organization_id,
    });
    return NextResponse.json(workspace, { status: 201 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
