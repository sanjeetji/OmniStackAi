import { NextRequest, NextResponse } from "next/server";
import { controlPlaneUrl } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  const { id } = await params;

  try {
    const cpRes = await fetch(
      `${controlPlaneUrl()}/projects/${encodeURIComponent(id)}/export`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      },
    );

    if (!cpRes.ok) {
      const errBody = await cpRes.json().catch(() => ({ error: "export failed" }));
      return NextResponse.json(errBody, { status: cpRes.status });
    }

    const headers = new Headers();
    headers.set("Content-Type", cpRes.headers.get("Content-Type") || "application/zip");
    const contentDisp = cpRes.headers.get("Content-Disposition");
    if (contentDisp) {
      headers.set("Content-Disposition", contentDisp);
    } else {
      headers.set("Content-Disposition", `attachment; filename="project-${id}.zip"`);
    }
    const contentLength = cpRes.headers.get("Content-Length");
    if (contentLength) {
      headers.set("Content-Length", contentLength);
    }

    return new Response(cpRes.body, {
      status: 200,
      headers,
    });
  } catch {
    return NextResponse.json(
      { error: "could not reach the control-plane" },
      { status: 502 },
    );
  }
}
