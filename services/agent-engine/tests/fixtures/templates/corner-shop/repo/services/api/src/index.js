import http from "node:http";
import pg from "pg";

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

function send(res, code, body) {
  res.writeHead(code, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  try {
    if (url.pathname === "/health") {
      await pool.query("SELECT 1");
      return send(res, 200, { status: "ok" });
    }
    if (url.pathname === "/products" && req.method === "GET") {
      const { rows } = await pool.query("SELECT id, name, price_cents FROM products ORDER BY name");
      return send(res, 200, { products: rows });
    }
    return send(res, 404, { error: "not found" });
  } catch {
    return send(res, 500, { error: "database error" });
  }
});

server.listen(Number(process.env.PORT || 4000), "127.0.0.1");
