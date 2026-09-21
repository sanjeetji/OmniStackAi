import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, createProjectFromTemplate } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

/** POST /api/templates/{slug}/use: create the caller's own project from a template (R-523). */
export async function POST(request: NextRequest, { params }: { params: Promise<{ slug: string }> }) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const { slug } = await params;
  const body = (await request.json().catch(() => ({}))) as { name?: unknown };
  const name = typeof body.name === "string" ? body.name.trim().slice(0, 120) : undefined;
  try {
    const created = await createProjectFromTemplate(token, slug, name ? { name } : {});
    return NextResponse.json(created, { status: 201 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
