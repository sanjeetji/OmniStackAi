import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  deleteProjectSecret,
  setProjectSecret,
  SetSecretParams,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; key: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, key } = await params;
  let body: SetSecretParams;
  try {
    body = (await request.json()) as SetSecretParams;
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  if (!body.value && body.value !== "") {
    return NextResponse.json({ error: "value is required" }, { status: 400 });
  }

  try {
    const secret = await setProjectSecret(token, id, key, body);
    return NextResponse.json(secret, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; key: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, key } = await params;
  try {
    await deleteProjectSecret(token, id, key);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
