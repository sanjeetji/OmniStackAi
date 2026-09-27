import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, actOnProjectLive, getProjectLive, type LiveAction } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-008: GET reports the live app; POST {action: publish | rollback | unpublish} acts on it.
const ACTIONS: LiveAction[] = ["publish", "rollback", "unpublish"];

function failure(error: unknown) {
  if (error instanceof ControlPlaneError) {
    return NextResponse.json({ error: error.message }, { status: error.status });
  }
  return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
}

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const { id } = await params;
  try {
    return NextResponse.json(await getProjectLive(token, id), { status: 200 });
  } catch (error) {
    return failure(error);
  }
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const { id } = await params;
  const body = (await request.json().catch(() => ({}))) as { action?: string; deleteData?: boolean };
  const action = (ACTIONS as string[]).includes(body.action ?? "") ? (body.action as LiveAction) : "publish";
  try {
    const status = await actOnProjectLive(token, id, action, { deleteData: body.deleteData });
    return NextResponse.json(status, { status: action === "publish" ? 202 : 200 });
  } catch (error) {
    return failure(error);
  }
}
