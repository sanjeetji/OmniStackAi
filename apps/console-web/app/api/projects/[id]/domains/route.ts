import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  listProjectDomains,
  addProjectDomain,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  try {
    const data = await listProjectDomains(token, id);
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  try {
    const body = await request.json();
    const hostname = body?.hostname;
    if (!hostname || typeof hostname !== "string") {
      return NextResponse.json({ error: "hostname is required" }, { status: 400 });
    }

    const domain = await addProjectDomain(token, id, hostname, body.provider);
    return NextResponse.json(domain, { status: 201 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}
