"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ShoppingBag,
  Search,
  User as UserIcon,
  Package,
  Layers,
  Store,
  ChevronDown,
} from "lucide-react";
import { api, type Cart, type Category } from "@bazaar/shared";

export function Header() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [cartCount, setCartCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    // Load categories
    api.getCategories()
      .then(setCategories)
      .catch((e) => console.error(e));

    // Check user & cart
    const rawUser = typeof localStorage !== "undefined" ? localStorage.getItem("bazaar_user") : null;
    if (rawUser) {
      try {
        setUser(JSON.parse(rawUser));
      } catch {}
    }

    // The cart belongs to a signed-in shopper. Asking for it while signed out is a 401 on every
    // public page, so only poll once there is a session.
    const signedIn = typeof localStorage !== "undefined" && Boolean(localStorage.getItem("bazaar_token"));
    if (!signedIn) {
      setCartCount(0);
      return;
    }

    const loadCart = async () => {
      try {
        const cart = await api.getCart();
        const total = (cart.items || []).reduce((acc, item) => acc + item.quantity, 0);
        setCartCount(total);
      } catch {
        setCartCount(0);
      }
    };
    loadCart();

    const interval = setInterval(loadCart, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/category/all?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="sticky top-8 z-40 bg-white/95 backdrop-blur-md border-b border-stone-200">
      {/* Top Banner Ticker */}
      <div className="bg-amber-50 text-amber-900 border-b border-amber-100 text-[11px] py-1 px-4 text-center font-medium">
        Authentic Handloom & Crafts directly from Indian artisans • Use code <span className="font-bold underline">WELCOME10</span> for 10% off
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5">
        <div className="flex items-center justify-between gap-4 sm:gap-8">
          {/* Brand Logo */}
          <Link href="/" className="flex items-center gap-2.5 shrink-0 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-700 to-amber-500 flex items-center justify-center text-white shadow-sm group-hover:scale-105 transition-transform">
              <ShoppingBag className="w-5 h-5" />
            </div>
            <div>
              <span className="text-2xl font-serif font-black tracking-tight text-stone-900">
                Bazaar
              </span>
              <span className="block text-[10px] uppercase font-bold tracking-widest text-amber-700">
                Artisan Marketplace
              </span>
            </div>
          </Link>

          {/* Search Box */}
          <form onSubmit={handleSearch} className="flex-1 max-w-xl hidden md:block">
            <div className="relative">
              <Search className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search handloom sarees, terracotta decor, spices, jewelry..."
                className="w-full pl-10 pr-4 py-2 bg-stone-100 hover:bg-stone-100/80 focus:bg-white text-sm rounded-full border border-transparent focus:border-amber-600 focus:outline-none focus:ring-2 focus:ring-amber-500/20 transition-all placeholder:text-stone-400"
              />
            </div>
          </form>

          {/* Nav Actions */}
          <div className="flex items-center gap-2 sm:gap-4 shrink-0">
            <Link
              href="/orders"
              className="p-2 text-stone-600 hover:text-amber-800 hover:bg-amber-50/60 rounded-lg flex items-center gap-1.5 text-xs font-semibold transition-colors"
            >
              <Package className="w-4 h-4 text-stone-500" />
              <span className="hidden sm:inline">My Orders</span>
            </Link>

            <Link
              href="/cart"
              className="relative p-2 text-stone-800 hover:text-amber-800 hover:bg-amber-50/60 rounded-lg flex items-center gap-1.5 text-xs font-semibold transition-colors"
            >
              <ShoppingBag className="w-4 h-4 text-amber-700" />
              <span className="hidden sm:inline">Cart</span>
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-amber-600 text-white text-[10px] font-black w-5 h-5 rounded-full flex items-center justify-center shadow-xs">
                  {cartCount}
                </span>
              )}
            </Link>

            {user ? (
              <Link
                href="/account"
                className="p-1.5 pl-2.5 pr-3 text-stone-700 hover:text-stone-900 bg-stone-100 hover:bg-stone-200/80 rounded-full flex items-center gap-2 text-xs font-semibold transition-colors"
              >
                <div className="w-6 h-6 rounded-full bg-amber-600 text-white flex items-center justify-center text-[10px] font-bold">
                  {user.name?.[0] || "P"}
                </div>
                <span className="max-w-[80px] truncate">{user.name}</span>
              </Link>
            ) : (
              <Link
                href="/login"
                className="px-3.5 py-1.5 bg-amber-700 hover:bg-amber-800 text-white rounded-full text-xs font-semibold shadow-xs transition-colors flex items-center gap-1.5"
              >
                <UserIcon className="w-3.5 h-3.5" />
                Sign In
              </Link>
            )}
          </div>
        </div>

        {/* Secondary Category Navigation Strip */}
        <nav aria-label="Product Categories" className="flex items-center gap-6 mt-3 pt-2.5 border-t border-stone-100 overflow-x-auto text-xs font-medium text-stone-600 whitespace-nowrap scrollbar-none">
          <Link href="/" className="hover:text-amber-800 transition-colors flex items-center gap-1">
            <Store className="w-3.5 h-3.5 text-amber-600" />
            All Shops
          </Link>
          {categories.map((c) => (
            <Link
              key={c.id}
              href={`/category/${c.slug}`}
              className="hover:text-amber-800 hover:underline transition-colors"
            >
              {c.name}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
