"use client";

import { useEffect, useState } from "react";

// Browser-side call through the preview proxy (NEXT_PUBLIC_API_URL).
export default function LiveCount() {
  const [count, setCount] = useState(null);
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/products`)
      .then((r) => r.json())
      .then((body) => setCount(body.products.length))
      .catch(() => setCount(-1));
  }, []);
  return <p id="live-count">Live products: {count ?? "..."}</p>;
}
