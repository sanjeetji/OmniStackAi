import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  createProjectRepo,
  type CreateRepoParams,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  let body: CreateRepoParams;
  try {
    body = (await request.json()) as CreateRepoParams;
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  try {
    const status = await createProjectRepo(token, id, body);
    return NextResponse.json(status, { status: 201 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: "could not reach the control-plane" },
      { status: 502 },
    );
  }
}
