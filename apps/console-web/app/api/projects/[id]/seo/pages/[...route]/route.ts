import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  setProjectPageSEO,
  type ProjectPageSEO,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; route: string[] }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, route: routeSegments } = await params;
  const rawRoute = routeSegments.join("/");
  const route = "/" + (rawRoute === "root" || rawRoute === "_root" ? "" : rawRoute);

  let body: Partial<ProjectPageSEO>;
  try {
    body = (await request.json()) as Partial<ProjectPageSEO>;
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  try {
    const result = await setProjectPageSEO(token, id, route, body);
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
