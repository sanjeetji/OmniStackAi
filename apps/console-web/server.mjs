// The console's server: Next.js as `next start` / `next dev` would run it, plus one thing a route
// handler cannot do - carry a WebSocket (PC-101). A preview's dev server keeps a WebSocket open at
// `<its base path>/_next/webpack-hmr` for live reload; through the console that upgrade reached no
// one, so every preview page logged failed connections and never refreshed after an edit.
//
// Only that path is forwarded, and only the way the HTTP preview proxy forwards anything: the
// session cookie must resolve the project through the control plane, and the target must be the
// preview's own loopback address. Every other upgrade goes to Next (the console's own dev reload).
//
// Usage: node server.mjs start|dev [-p <port>]
import http from "node:http";
import next from "next";

const mode = process.argv[2] === "dev" ? "dev" : "start";
const portFlag = process.argv.indexOf("-p");
const port = Number(portFlag > 0 ? process.argv[portFlag + 1] : process.env.PORT || 3000);
const controlPlane = process.env.OMNISTACKAI_CONTROL_PLANE_URL ?? "http://127.0.0.1:8080";
const LOOPBACK = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);
const SESSION_COOKIE = "omnistackai_session";

const app = next({ dev: mode === "dev", port });
await app.prepare();
const handle = app.getRequestHandler();
const nextUpgrade = app.getUpgradeHandler();

function sessionToken(cookieHeader) {
  for (const part of (cookieHeader || "").split(";")) {
    const [name, ...value] = part.trim().split("=");
    if (name === SESSION_COOKIE) return decodeURIComponent(value.join("="));
  }
  return null;
}

/** The loopback origin and path a preview's reload socket lives at, or null. */
async function hmrTarget(pathname, cookieHeader) {
  const match = pathname.match(/^\/preview\/([^/]+)\/(.*)$/);
  if (!match || !pathname.endsWith("/_next/webpack-hmr")) return null;
  const token = sessionToken(cookieHeader);
  if (!token) return null;
  const [, projectId, rest] = match;
  const response = await fetch(`${controlPlane}/projects/${projectId}/preview`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) return null;
  const preview = await response.json();
  if (preview.status !== "ready") return null;
  let origin;
  let path;
  if (preview.kind === "multi" && Array.isArray(preview.apps)) {
    // Each app runs under its base path, so the path is forwarded unchanged.
    const appId = rest.split("/")[0];
    const target = preview.apps.find((candidate) => candidate.id === appId);
    if (!target || target.kind === "api" || !target.ready) return null;
    origin = new URL(target.url);
    path = pathname;
  } else {
    if (!preview.web_url) return null;
    origin = new URL(preview.web_url);
    path = `/${rest}`;
  }
  if (!LOOPBACK.has(origin.hostname)) return null;
  return { origin, path };
}

function refuse(socket, status, reason) {
  socket.end(`HTTP/1.1 ${status} ${reason}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n`);
}

const server = http.createServer((req, res) => handle(req, res));

const isPreviewUpgrade = (req) => (req.url || "").startsWith("/preview/");

// Next attaches its own upgrade listener to this server on the first request, and it closes any
// socket it does not recognise - before the check below (which waits on the control plane) could
// answer. Preview reload sockets therefore go to this handler alone; every other upgrade goes to
// whatever listeners Next has registered (or to Next's handler when it has registered none yet).
const emit = server.emit.bind(server);
server.emit = (event, ...args) => {
  if (event !== "upgrade") return emit(event, ...args);
  const [req, socket, head] = args;
  if (isPreviewUpgrade(req)) {
    void previewUpgrade(req, socket, head);
    return true;
  }
  if (server.listenerCount("upgrade") === 0) {
    nextUpgrade(req, socket, head);
    return true;
  }
  return emit(event, ...args);
};

async function previewUpgrade(req, socket, head) {
  const url = new URL(req.url || "/", "http://console.local");
  let target;
  try {
    target = await hmrTarget(url.pathname, req.headers.cookie);
  } catch {
    target = null;
  }
  if (!target) return refuse(socket, 404, "Not Found");

  const headers = { ...req.headers, host: target.origin.host };
  // The dev server accepts its reload socket only from its own origin (allowedDevOrigins); the
  // console has checked the session and the project, as the HTTP proxy does before it rewrites it.
  if (headers.origin) headers.origin = target.origin.origin;
  delete headers.cookie; // the console's session never reaches the app
  const upstream = http.request({
    hostname: target.origin.hostname,
    port: target.origin.port,
    path: `${target.path}${url.search}`,
    method: "GET",
    headers,
  });
  upstream.on("upgrade", (response, upstreamSocket, upstreamHead) => {
    const lines = [`HTTP/1.1 101 ${response.statusMessage || "Switching Protocols"}`];
    for (let i = 0; i < response.rawHeaders.length; i += 2) {
      lines.push(`${response.rawHeaders[i]}: ${response.rawHeaders[i + 1]}`);
    }
    socket.write(lines.join("\r\n") + "\r\n\r\n");
    if (upstreamHead.length) socket.write(upstreamHead);
    if (head.length) upstreamSocket.write(head);
    upstreamSocket.pipe(socket).pipe(upstreamSocket);
    const close = () => { socket.destroy(); upstreamSocket.destroy(); };
    socket.on("error", close);
    upstreamSocket.on("error", close);
    socket.on("close", close);
    upstreamSocket.on("close", close);
  });
  upstream.on("response", (response) => {
    refuse(socket, response.statusCode || 502, response.statusMessage || "Bad Gateway");
    response.resume();
  });
  upstream.on("error", () => refuse(socket, 502, "Bad Gateway"));
  upstream.end();
}

server.listen(port, () => {
  console.log(`OmniStackAI console (${mode}) on http://127.0.0.1:${port}`);
});
