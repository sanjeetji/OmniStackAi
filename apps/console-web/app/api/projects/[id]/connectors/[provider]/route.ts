import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  saveProjectConnector,
  deleteProjectConnector,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; provider: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, provider } = await params;
  try {
    const body = await request.json();
    const config = body?.config || {};
    const enabled = body?.enabled !== undefined ? Boolean(body.enabled) : true;

    const data = await saveProjectConnector(token, id, provider, config, enabled);
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; provider: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, provider } = await params;
  try {
    const data = await deleteProjectConnector(token, id, provider);
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}
