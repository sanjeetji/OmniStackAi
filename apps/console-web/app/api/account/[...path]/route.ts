import { NextRequest, NextResponse } from "next/server";
import { controlPlaneUrl } from "@/lib/control-plane";
import { getSessionToken, isSecureRequest, SESSION_COOKIE_NAME } from "@/lib/session";

// PC-012: account basics (verify email, password reset, export, delete), carried to the control
// plane's /auth routes. Only these paths are forwarded; the control plane decides everything.
type Params = { params: Promise<{ path: string[] }> };

const ROUTES: Record<string, { method: "GET" | "POST"; signedIn: boolean; signsOut?: boolean }> = {
  "verify-email": { method: "POST", signedIn: false },
  "verify-email/resend": { method: "POST", signedIn: true },
  "forgot-password": { method: "POST", signedIn: false },
  "reset-password": { method: "POST", signedIn: false, signsOut: true },
  "me/export": { method: "GET", signedIn: true },
  "me/delete": { method: "POST", signedIn: true, signsOut: true },
};

async function handle(request: NextRequest, { params }: Params) {
  const path = (await params).path.join("/");
  const route = ROUTES[path];
  if (!route || route.method !== request.method) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }
  const token = await getSessionToken();
  if (route.signedIn && !token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  let upstream: Response;
  try {
    upstream = await fetch(`${controlPlaneUrl()}/auth/${path}`, {
      method: route.method,
      headers,
      body: route.method === "POST" ? await request.text() : undefined,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
  const outHeaders: Record<string, string> = {
    "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
  };
  const disposition = upstream.headers.get("Content-Disposition");
  if (disposition) outHeaders["Content-Disposition"] = disposition;
  const response = new NextResponse(await upstream.text(), { status: upstream.status, headers: outHeaders });
  // A reset signs every session out and a deletion removes the account: drop the local cookie too.
  if (route.signsOut && upstream.ok) {
    response.cookies.set(SESSION_COOKIE_NAME, "", {
      httpOnly: true,
      sameSite: "lax",
      secure: isSecureRequest(request),
      path: "/",
      maxAge: 0,
    });
  }
  return response;
}

export const GET = handle;
export const POST = handle;
