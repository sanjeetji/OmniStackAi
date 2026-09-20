import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  revealProjectSecret,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; key: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, key } = await params;
  try {
    const revealed = await revealProjectSecret(token, id, key);
    return NextResponse.json(revealed, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
