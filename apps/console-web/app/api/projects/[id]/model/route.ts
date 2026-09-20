import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  getProjectModel,
  setProjectModel,
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
    const modelConfig = await getProjectModel(token, id);
    return NextResponse.json(modelConfig, { status: 200 });
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
  let body: { model_provider_id?: string; model_id?: string };
  try {
    body = (await request.json()) as { model_provider_id?: string; model_id?: string };
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  try {
    const result = await setProjectModel(
      token,
      id,
      (body.model_provider_id || "").trim(),
      (body.model_id || "").trim()
    );
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
