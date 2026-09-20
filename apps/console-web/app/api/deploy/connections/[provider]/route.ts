import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  deleteDeployConnection,
  getDeployConnection,
  saveDeployConnection,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ provider: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { provider } = await params;
  if (provider !== "vercel" && provider !== "netlify") {
    return NextResponse.json({ error: "invalid provider" }, { status: 400 });
  }

  try {
    const status = await getDeployConnection(token, provider);
    return NextResponse.json(status, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ provider: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { provider } = await params;
  if (provider !== "vercel" && provider !== "netlify") {
    return NextResponse.json({ error: "invalid provider" }, { status: 400 });
  }

  try {
    const body = await request.json();
    const apiKey = typeof body.api_key === "string" ? body.api_key.trim() : "";
    const accountLabel = typeof body.account_label === "string" ? body.account_label.trim() : undefined;

    if (!apiKey) {
      return NextResponse.json({ error: "api_key is required" }, { status: 400 });
    }

    const status = await saveDeployConnection(token, provider, apiKey, accountLabel);
    return NextResponse.json(status, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ provider: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { provider } = await params;
  if (provider !== "vercel" && provider !== "netlify") {
    return NextResponse.json({ error: "invalid provider" }, { status: 400 });
  }

  try {
    const res = await deleteDeployConnection(token, provider);
    return NextResponse.json(res, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}
