import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  getProjectKnowledge,
  updateProjectKnowledge,
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
    const knowledge = await getProjectKnowledge(token, id);
    return NextResponse.json(knowledge, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  let body: { knowledge: string };
  try {
    body = (await request.json()) as { knowledge: string };
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  if (typeof body.knowledge !== "string") {
    return NextResponse.json({ error: "knowledge field is required" }, { status: 400 });
  }

  try {
    const knowledge = await updateProjectKnowledge(token, id, body.knowledge);
    return NextResponse.json(knowledge, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
