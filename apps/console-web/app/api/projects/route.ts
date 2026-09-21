import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  createProject,
  listProjects,
  type CreateProjectRequest,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status") ?? undefined;
  const sort = searchParams.get("sort") ?? undefined;
  const workspaceId = searchParams.get("workspace_id") ?? undefined;
  const limitParam = searchParams.get("limit");
  const offsetParam = searchParams.get("offset");
  const limit = limitParam ? parseInt(limitParam, 10) : undefined;
  const offset = offsetParam ? parseInt(offsetParam, 10) : undefined;

  try {
    const data = await listProjects(token, { status, sort, limit, offset, workspace_id: workspaceId });
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

  let body: CreateProjectRequest;
  try {
    body = (await request.json()) as CreateProjectRequest;
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  if (typeof body.name !== "string" || body.name.trim().length === 0) {
    return NextResponse.json({ error: "name is required" }, { status: 400 });
  }

  try {
    const project = await createProject(token, {
      name: body.name.trim(),
      description: body.description?.trim(),
      prompt: body.prompt?.trim(),
      workspace_id: body.workspace_id,
    });
    return NextResponse.json(project, { status: 201 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
