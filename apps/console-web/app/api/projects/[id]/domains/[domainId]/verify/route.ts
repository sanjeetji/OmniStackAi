import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  verifyProjectDomain,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; domainId: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, domainId } = await params;
  try {
    const res = await verifyProjectDomain(token, id, domainId);
    return NextResponse.json(res, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}
