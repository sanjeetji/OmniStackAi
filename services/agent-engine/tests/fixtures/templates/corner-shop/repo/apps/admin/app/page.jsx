export const dynamic = "force-dynamic";

export default async function Admin() {
  const response = await fetch(`${process.env.API_URL}/products`, { cache: "no-store" });
  const count = response.ok ? (await response.json()).products.length : 0;
  return (
    <main>
      <h1>Corner Shop admin</h1>
      <p id="product-count">Products in stock: {count}</p>
    </main>
  );
}
