import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  deleteUserKey,
  getUserKey,
  setUserKey,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ providerId: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { providerId } = await params;
  try {
    const key = await getUserKey(token, providerId);
    return NextResponse.json(key, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ providerId: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { providerId } = await params;
  let body: { api_key?: string; label?: string };
  try {
    body = (await request.json()) as { api_key?: string; label?: string };
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  if (!body.api_key || !body.api_key.trim()) {
    return NextResponse.json({ error: "api_key is required" }, { status: 400 });
  }

  try {
    const result = await setUserKey(token, providerId, body.api_key.trim(), (body.label || "").trim());
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ providerId: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { providerId } = await params;
  try {
    const result = await deleteUserKey(token, providerId);
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
