import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, getEstimate } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

// PC-010: what a build or edit will cost, before it starts. ?kind=build|edit&project=<id>
export async function GET(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) return NextResponse.json({ error: "not signed in" }, { status: 401 });
  const kind = request.nextUrl.searchParams.get("kind") === "edit" ? "edit" : "build";
  const project = request.nextUrl.searchParams.get("project") || undefined;
  try {
    return NextResponse.json(await getEstimate(token, kind, project), { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
