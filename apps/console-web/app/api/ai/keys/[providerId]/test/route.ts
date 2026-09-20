import { NextRequest, NextResponse } from "next/server";
import { ControlPlaneError, testUserKey } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ providerId: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { providerId } = await params;
  let body: { api_key?: string } = {};
  try {
    body = (await request.json()) as { api_key?: string };
  } catch {
    // empty body is allowed when testing existing key
  }

  try {
    const result = await testUserKey(token, providerId, body.api_key);
    return NextResponse.json(result, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
