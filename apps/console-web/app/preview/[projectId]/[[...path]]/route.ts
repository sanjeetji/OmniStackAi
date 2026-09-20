import { NextRequest, NextResponse } from "next/server";
import { getProjectPreview } from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

interface RouteParams {
  params: Promise<{
    projectId: string;
    path?: string[];
  }>;
}

const ALLOWED_LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);

async function handleProxy(request: NextRequest, { params }: RouteParams): Promise<Response> {
  // Check if preview proxy is explicitly disabled via env var
  if (process.env.OMNISTACKAI_PREVIEW_PROXY === "0") {
    return NextResponse.json({ error: "preview proxy is disabled" }, { status: 404 });
  }

  const { projectId, path: rawPath } = await params;
  const pathSegments = rawPath ?? [];

  // Tenant Isolation & Authentication: require active session
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "project not found" }, { status: 404 });
  }

  // Resolve verified preview status and ports server-side via control-plane
  let preview;
  try {
    preview = await getProjectPreview(token, projectId);
  } catch {
    // Foreign project or non-existent project returns 404 (never leak foreign existence)
    return NextResponse.json({ error: "project not found" }, { status: 404 });
  }

  if (preview.status !== "ready" || !preview.web_url) {
    const message = preview.message || "Preview is not ready yet.";
    return new NextResponse(
      `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Preview</title><style>body{font-family:system-ui,sans-serif;display:grid;place-content:center;height:100vh;margin:0;background:#09090b;color:#a1a1aa;text-align:center}</style></head><body><h2>Preview Not Ready</h2><p>${escapeHtml(message)}</p></body></html>`,
      { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
    );
  }

  // SSRF Prevention: strict loopback validation on target URL
  const isApi = pathSegments.length > 0 && pathSegments[0] === "api";
  let targetBase = preview.web_url;
  let targetPath = "/" + pathSegments.join("/");

  if (isApi) {
    if (preview.api_url) {
      targetBase = preview.api_url;
      const subSegments = pathSegments.slice(1);
      targetPath = "/" + subSegments.join("/");
    } else {
      targetBase = preview.web_url;
      targetPath = "/" + pathSegments.join("/");
    }
  }

  let parsedTarget: URL;
  try {
    parsedTarget = new URL(targetBase);
  } catch {
    return NextResponse.json({ error: "invalid preview target" }, { status: 502 });
  }

  if (!ALLOWED_LOOPBACK_HOSTS.has(parsedTarget.hostname)) {
    // Defense in depth: strictly reject any non-loopback host
    return NextResponse.json({ error: "forbidden target host" }, { status: 403 });
  }

  const query = request.nextUrl.search || "";
  const upstreamUrl = `${parsedTarget.origin}${targetPath}${query}`;

  // Forward request headers, stripping hop-by-hop and host headers
  const forwardHeaders = new Headers();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (
      lower !== "host" &&
      lower !== "connection" &&
      lower !== "content-length" &&
      lower !== "transfer-encoding"
    ) {
      forwardHeaders.set(key, value);
    }
  });

  const method = request.method;
  const hasBody = !["GET", "HEAD"].includes(method);

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(upstreamUrl, {
      method,
      headers: forwardHeaders,
      body: hasBody ? request.body : undefined,
      redirect: "manual",
      // @ts-expect-error duplex is required by Next.js edge/node fetch for streaming request body
      duplex: "half",
    });
  } catch {
    return NextResponse.json({ error: "could not reach preview service" }, { status: 502 });
  }

  // Build response headers
  const responseHeaders = new Headers();
  upstreamResponse.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower !== "content-length" && lower !== "transfer-encoding") {
      responseHeaders.set(key, value);
    }
  });

  // Rewrite Location header for redirects so the client stays within the proxy
  const locationHeader = upstreamResponse.headers.get("location");
  if (locationHeader) {
    let rewrittenLocation = locationHeader;
    const prefix = `/preview/${encodeURIComponent(projectId)}`;
    if (rewrittenLocation.startsWith(parsedTarget.origin)) {
      rewrittenLocation = rewrittenLocation.slice(parsedTarget.origin.length);
    }
    if (rewrittenLocation.startsWith("/")) {
      rewrittenLocation = `${prefix}${rewrittenLocation}`;
    }
    responseHeaders.set("location", rewrittenLocation);
  }

  const contentType = upstreamResponse.headers.get("content-type") || "";

  // HTML Rewriting: inject base href and rewrite root-relative asset prefixes
  if (contentType.includes("text/html")) {
    const text = await upstreamResponse.text();
    const prefix = `/preview/${encodeURIComponent(projectId)}`;
    const baseTag = `<base href="${prefix}/">`;

    let rewritten = text;
    if (rewritten.includes("<head>")) {
      rewritten = rewritten.replace("<head>", `<head>${baseTag}`);
    } else if (rewritten.includes("<head ")) {
      rewritten = rewritten.replace(/<head[^>]*>/, `$&${baseTag}`);
    } else {
      rewritten = `${baseTag}${rewritten}`;
    }

    // Rewrite Next.js chunk and static asset paths to route through proxy
    rewritten = rewritten.replaceAll("/_next/", `${prefix}/_next/`);

    // Rewrite loopback API / web URLs that might have been baked in
    if (preview.api_port) {
      rewritten = rewritten.replaceAll(`http://127.0.0.1:${preview.api_port}`, `${prefix}/api`);
      rewritten = rewritten.replaceAll(`http://localhost:${preview.api_port}`, `${prefix}/api`);
    }
    if (preview.web_port) {
      rewritten = rewritten.replaceAll(`http://127.0.0.1:${preview.web_port}`, `${prefix}`);
      rewritten = rewritten.replaceAll(`http://localhost:${preview.web_port}`, `${prefix}`);
    }

    return new NextResponse(rewritten, {
      status: upstreamResponse.status,
      headers: responseHeaders,
    });
  }

  // Stream assets, JS, JSON, and media directly
  return new NextResponse(upstreamResponse.body, {
    status: upstreamResponse.status,
    headers: responseHeaders,
  });
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const PATCH = handleProxy;
export const DELETE = handleProxy;
export const HEAD = handleProxy;
export const OPTIONS = handleProxy;
