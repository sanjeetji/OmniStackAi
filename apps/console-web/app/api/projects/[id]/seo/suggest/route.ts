import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  suggestProjectSEOCopy,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;
  let body: { route?: string; page_name?: string };
  try {
    body = (await request.json()) as { route?: string; page_name?: string };
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  try {
    const suggestion = await suggestProjectSEOCopy(token, id, body.route || "/", body.page_name);
    return NextResponse.json(suggestion, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
