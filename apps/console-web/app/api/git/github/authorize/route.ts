import { NextRequest, NextResponse } from "next/server";
import { controlPlaneUrl } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  try {
    const cpRes = await fetch(`${controlPlaneUrl()}/git/github/authorize`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    });

    const data = await cpRes.json().catch(() => ({}));
    if (!cpRes.ok) {
      return NextResponse.json(data, { status: cpRes.status });
    }

    const authUrl = data.url;
    const acceptHeader = request.headers.get("accept") ?? "";
    const isNavigation =
      acceptHeader.includes("text/html") && !request.nextUrl.searchParams.has("json");

    if (isNavigation && authUrl) {
      return NextResponse.redirect(authUrl, 302);
    }

    return NextResponse.json(data, { status: 200 });
  } catch {
    return NextResponse.json(
      { error: "could not reach the control-plane" },
      { status: 502 },
    );
  }
}
