import { controlPlaneUrl } from "@/lib/control-plane";

/** Template covers and screenshots (R-523), relayed from the public control-plane catalogue. Only
 * files a template's manifest declares exist upstream; anything else is a 404. */
export async function GET(_request: Request, { params }: { params: Promise<{ slug: string; path: string[] }> }) {
  const { slug, path } = await params;
  const upstreamPath = path.map((segment) => encodeURIComponent(segment)).join("/");
  let upstream: Response;
  try {
    upstream = await fetch(
      `${controlPlaneUrl()}/templates/${encodeURIComponent(slug)}/assets/${upstreamPath}`,
      { cache: "no-store" },
    );
  } catch {
    return new Response("template catalogue unavailable", { status: 502 });
  }
  if (!upstream.ok) {
    return new Response("not found", { status: 404 });
  }
  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/octet-stream",
      "Cache-Control": "public, max-age=3600",
      "X-Content-Type-Options": "nosniff",
      // SVG covers are images, never documents that can run script.
      "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
    },
  });
}
