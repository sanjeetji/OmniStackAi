import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, testProjectConnector } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; provider: string }> }
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id, provider } = await params;
  try {
    let config: Record<string, any> | undefined;
    try {
      const body = await request.json();
      config = body?.config;
    } catch {
      // Body may be empty
    }

    const result = await testProjectConnector(token, id, provider, config);
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach control-plane" }, { status: 502 });
  }
}
