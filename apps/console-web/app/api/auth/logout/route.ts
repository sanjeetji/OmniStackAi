import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { logout } from "@/lib/control-plane";
import { getSessionToken, isSecureRequest, SESSION_COOKIE_NAME } from "@/lib/session";

// Logout is idempotent and always clears the local cookie, even if the control-plane call fails -
// a network hiccup must never leave someone stuck "signed in" with no way to sign out locally.
export async function POST(request: NextRequest) {
  const token = await getSessionToken();
  if (token) {
    await logout(token);
  }

  const response = new NextResponse(null, { status: 204 });
  response.cookies.set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: isSecureRequest(request),
    path: "/",
    maxAge: 0,
  });
  return response;
}
