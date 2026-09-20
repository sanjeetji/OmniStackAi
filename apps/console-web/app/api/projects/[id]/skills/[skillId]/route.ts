import { NextRequest, NextResponse } from "next/server";
import {
  attachProjectSkill,
  ControlPlaneError,
  detachProjectSkill,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function PUT(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; skillId: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, skillId } = await params;
  try {
    const result = await attachProjectSkill(token, id, skillId);
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
  { params }: { params: Promise<{ id: string; skillId: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, skillId } = await params;
  try {
    const result = await detachProjectSkill(token, id, skillId);
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
