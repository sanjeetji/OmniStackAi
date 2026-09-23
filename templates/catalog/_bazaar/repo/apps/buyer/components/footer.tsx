import Link from "next/link";
import { ShieldCheck, Truck, RotateCcw, HeartHandshake, Sparkles } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-stone-900 text-stone-300 mt-20 border-t border-stone-800">
      {/* Value Proposition Highlights */}
      <div className="border-b border-stone-800 bg-stone-950/60 py-10 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-amber-900/30 text-amber-400 rounded-xl border border-amber-800/40 shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold">100% Genuine Handcrafted</h4>
              <p className="text-stone-400 text-xs mt-1 leading-relaxed">
                Directly certified by weaving societies, state clusters, and GI tags.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-amber-900/30 text-amber-400 rounded-xl border border-amber-800/40 shrink-0">
              <HeartHandshake className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold">Direct Artisan Fair Share</h4>
              <p className="text-stone-400 text-xs mt-1 leading-relaxed">
                Up to 90% of order value goes directly to creator bank accounts.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-amber-900/30 text-amber-400 rounded-xl border border-amber-800/40 shrink-0">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold">Tracked Express Delivery</h4>
              <p className="text-stone-400 text-xs mt-1 leading-relaxed">
                Real-time tracking checkpoints from the artisan’s workshop to your door.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="p-2.5 bg-amber-900/30 text-amber-400 rounded-xl border border-amber-800/40 shrink-0">
              <RotateCcw className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold">Easy 7-Day Returns</h4>
              <p className="text-stone-400 text-xs mt-1 leading-relaxed">
                Complete purchase protection with transparent refund settlements.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Footer Links */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <h4 className="text-white text-xs uppercase font-bold tracking-wider mb-3">Shop Categories</h4>
            <ul className="space-y-2 text-xs">
              <li><Link href="/category/apparel-ethnic" className="hover:text-amber-400 transition-colors">Handloom Sarees & Kurtas</Link></li>
              <li><Link href="/category/home-decor" className="hover:text-amber-400 transition-colors">Studio Pottery & Terracotta</Link></li>
              <li><Link href="/category/home-decor" className="hover:text-amber-400 transition-colors">Brass Urli & Planters</Link></li>
              <li><Link href="/category/gourmet-spices" className="hover:text-amber-400 transition-colors">Single-Origin Spices</Link></li>
              <li><Link href="/category/jewelry-crafts" className="hover:text-amber-400 transition-colors">92.5 Sterling Silver</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white text-xs uppercase font-bold tracking-wider mb-3">Artisan Shops</h4>
            <ul className="space-y-2 text-xs">
              <li><Link href="/shops/craftloom" className="hover:text-amber-400 transition-colors">Craftloom Studio (Chanderi)</Link></li>
              <li><Link href="/shops/rangoli-silks" className="hover:text-amber-400 transition-colors">Rangoli Silks (Kanchipuram)</Link></li>
              <li><Link href="/shops/mitti-earth" className="hover:text-amber-400 transition-colors">Mitti Earth Studio</Link></li>
              <li><Link href="/shops/brass-bloom" className="hover:text-amber-400 transition-colors">Brass & Bloom</Link></li>
              <li><Link href="/shops/spice-route" className="hover:text-amber-400 transition-colors">Spice Route Organics</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white text-xs uppercase font-bold tracking-wider mb-3">Customer Care</h4>
            <ul className="space-y-2 text-xs">
              <li><Link href="/orders" className="hover:text-amber-400 transition-colors">Track Orders</Link></li>
              <li><Link href="/addresses" className="hover:text-amber-400 transition-colors">Saved Addresses</Link></li>
              <li><Link href="/reviews" className="hover:text-amber-400 transition-colors">Product Reviews</Link></li>
              <li><Link href="/account" className="hover:text-amber-400 transition-colors">Account Settings</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-white text-xs uppercase font-bold tracking-wider mb-3">OmniStackAI Template</h4>
            <p className="text-stone-400 text-xs leading-relaxed mb-4">
              Bazaar is an autonomous multi-vendor commerce template with shared carts, per-vendor split shipments, and double-entry accounting.
            </p>
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-stone-800 text-[11px] text-amber-400 font-medium border border-stone-700">
              <Sparkles className="w-3.5 h-3.5" />
              Demo Version 1.0.0
            </div>
          </div>
        </div>

        <div className="mt-12 pt-6 border-t border-stone-800 flex flex-col sm:flex-row items-center justify-between text-stone-500 text-xs gap-4">
          <p>© 2026 Bazaar Marketplace. Proudly built on the OmniStackAI platform.</p>
          <div className="flex items-center gap-4">
            <span>Zero Paid Credentials</span>
            <span>•</span>
            <span>Simulated Mock Providers</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
