import LiveCount from "./live-count";

export const dynamic = "force-dynamic";

async function products() {
  const response = await fetch(`${process.env.API_URL}/products`, { cache: "no-store" });
  if (!response.ok) return [];
  return (await response.json()).products;
}

export default async function Home() {
  const items = await products();
import Link from "next/link";
import LiveCount from "./live-count";

export const dynamic = "force-dynamic";

async function products() {
  const response = await fetch(`${process.env.API_URL}/products`, { cache: "no-store" });
  if (!response.ok) return [];
  return (await response.json()).products;
}

export default async function Home() {
  const items = await products();
  return (
    <main>
      <nav style={{ marginBottom: 20 }}>
        <Link href="/">Home</Link> | <Link href="/about">About Us</Link>
      </nav>
      <h1>Corner Shop</h1>
      <ul>
        {items.map((p) => (
          <li key={p.id}>
            {p.name} ({(p.price_cents / 100).toFixed(2)})
          </li>
        ))}
      </ul>
      <LiveCount />
    </main>
  );
}

