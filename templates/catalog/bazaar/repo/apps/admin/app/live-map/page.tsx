"use client";

import { useState, useEffect } from "react";
import { AdminHeader } from "@/components/admin-header";
import {
  MapPin,
  Truck,
  Activity,
  Radio,
  CheckCircle2,
  Clock,
  Layers,
  Store,
  Navigation,
} from "lucide-react";
import { formatCurrency } from "@bazaar/shared";

interface CraftHub {
  id: string;
  name: string;
  artisanCluster: string;
  giTag: string;
  state: string;
  x: number; // SVG coordinate percent
  y: number; // SVG coordinate percent
  activeDispatches: number;
  todayGmvCents: number;
}

export default function AdminLiveMapPage() {
  const [selectedHub, setSelectedHub] = useState<CraftHub | null>(null);

  const hubs: CraftHub[] = [
    {
      id: "hub-kashmir",
      name: "Srinagar Atelier Guild",
      artisanCluster: "Pashmina & Sozni Needlework",
      giTag: "GI #46",
      state: "Jammu & Kashmir",
      x: 32,
      y: 14,
      activeDispatches: 3,
      todayGmvCents: 4120000,
    },
    {
      id: "hub-jaipur",
      name: "Jaipur Blue Art Pottery",
      artisanCluster: "Quartz Ceramic Glazing",
      giTag: "GI #39",
      state: "Rajasthan",
      x: 30,
      y: 35,
      activeDispatches: 8,
      todayGmvCents: 6450000,
    },
    {
      id: "hub-varanasi",
      name: "Varanasi Heritage Weaves",
      artisanCluster: "Pure Katan Zari Brocade",
      giTag: "GI #69",
      state: "Uttar Pradesh",
      x: 58,
      y: 40,
      activeDispatches: 6,
      todayGmvCents: 8940000,
    },
    {
      id: "hub-bastar",
      name: "Bastar Tribal Bell Metal",
      artisanCluster: "Dhokra Lost-Wax Bronze",
      giTag: "GI #84",
      state: "Chhattisgarh",
      x: 52,
      y: 54,
      activeDispatches: 4,
      todayGmvCents: 2180000,
    },
    {
      id: "hub-channapatna",
      name: "Channapatna Wooden Toys",
      artisanCluster: "Natural Lacquer Turned Wood",
      giTag: "GI #19",
      state: "Karnataka",
      x: 37,
      y: 78,
      activeDispatches: 2,
      todayGmvCents: 1250000,
    },
    {
      id: "hub-kanchipuram",
      name: "Kanchipuram Silk Loom",
      artisanCluster: "Korvai Temple Border Silks",
      giTag: "GI #1",
      state: "Tamil Nadu",
      x: 44,
      y: 84,
      activeDispatches: 5,
      todayGmvCents: 7300000,
    },
  ];

  useEffect(() => {
    setSelectedHub(hubs[1]); // Default to Jaipur
  }, []);

  const totalActiveDispatches = hubs.reduce((acc, h) => acc + h.activeDispatches, 0);

  return (
    <div className="flex-1 flex flex-col">
      <AdminHeader
        title="Live Logistics Map"
        subtitle="Nationwide real-time tracking map showing live fulfillment density across artisan GI craft hubs."
        badge="Real-time Telemetry"
      />

      <div className="p-6 space-y-6 flex-1">
        {/* Top Ticker Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Active Courier Transit</div>
              <div className="text-2xl font-bold font-mono text-white mt-1">
                {totalActiveDispatches} Consignments
              </div>
            </div>
            <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Truck className="w-4 h-4" />
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Craft Clusters Online</div>
              <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
                6 GI Ateliers
              </div>
            </div>
            <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Store className="w-4 h-4" />
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Real-time SSE Radar</div>
              <div className="text-2xl font-bold font-mono text-emerald-400 mt-1 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                Live Feed
              </div>
            </div>
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Radio className="w-4 h-4" />
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Transit SLA Health</div>
              <div className="text-2xl font-bold font-mono text-white mt-1">
                99.8% On-Time
              </div>
            </div>
            <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
          </div>
        </div>

        {/* Map Canvas and Hub Inspection Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* India SVG Geographic Map */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden flex flex-col justify-between min-h-[480px]">
            <div className="flex items-center justify-between z-10 mb-2">
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <Navigation className="w-4 h-4 text-amber-400" />
                <span className="font-semibold text-white">Indian Artisan Geographic Dispatch Network</span>
              </div>
              <span className="text-[11px] font-mono text-slate-400">
                Click any marker to inspect cluster dispatches
              </span>
            </div>

            {/* Stylized SVG Map Container */}
            <div className="relative w-full h-[400px] flex items-center justify-center">
              {/* India Silhouette SVG */}
              <svg
                viewBox="0 0 600 650"
                className="w-full h-full max-h-[420px] text-slate-800 fill-current opacity-40"
              >
                {/* Simplified outline polygon of India */}
                <path d="M 230 40 L 260 20 L 280 50 L 300 30 L 330 60 L 320 110 L 350 140 L 390 140 L 440 180 L 490 180 L 510 210 L 470 230 L 430 220 L 390 260 L 370 290 L 360 340 L 330 380 L 300 420 L 270 480 L 260 540 L 250 580 L 245 610 L 240 580 L 220 520 L 200 460 L 180 400 L 170 340 L 140 320 L 110 320 L 90 280 L 110 240 L 150 220 L 180 180 L 200 130 Z" />
              </svg>

              {/* Transit Flight / Road Lines */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none stroke-amber-500/20 stroke-dasharray-4">
                <line x1="30%" y1="35%" x2="58%" y2="40%" strokeWidth="1.5" stroke="#f59e0b" strokeOpacity="0.3" strokeDasharray="4 4" />
                <line x1="32%" y1="14%" x2="30%" y2="35%" strokeWidth="1.5" stroke="#f59e0b" strokeOpacity="0.3" strokeDasharray="4 4" />
                <line x1="58%" y1="40%" x2="52%" y2="54%" strokeWidth="1.5" stroke="#f59e0b" strokeOpacity="0.3" strokeDasharray="4 4" />
                <line x1="52%" y1="54%" x2="44%" y2="84%" strokeWidth="1.5" stroke="#f59e0b" strokeOpacity="0.3" strokeDasharray="4 4" />
                <line x1="44%" y1="84%" x2="37%" y2="78%" strokeWidth="1.5" stroke="#f59e0b" strokeOpacity="0.3" strokeDasharray="4 4" />
                <line x1="37%" y1="78%" x2="30%" y2="35%" strokeWidth="1.5" stroke="#f59e0b" strokeOpacity="0.3" strokeDasharray="4 4" />
              </svg>

              {/* Interactive Hub Markers */}
              {hubs.map((hub) => {
                const isSelected = selectedHub?.id === hub.id;
                return (
                  <button
                    key={hub.id}
                    onClick={() => setSelectedHub(hub)}
                    style={{ left: `${hub.x}%`, top: `${hub.y}%` }}
                    className="absolute -translate-x-1/2 -translate-y-1/2 group cursor-pointer focus:outline-none z-20"
                  >
                    <div className="relative flex items-center justify-center">
                      <span
                        className={`absolute w-8 h-8 rounded-full ${
                          isSelected
                            ? "bg-amber-400/30 animate-ping"
                            : "bg-amber-500/10 group-hover:scale-125 transition-transform"
                        }`}
                      />
                      <div
                        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-[9px] font-bold font-mono transition shadow-lg ${
                          isSelected
                            ? "bg-amber-500 border-white text-slate-950 scale-110 shadow-amber-500/50"
                            : "bg-slate-900 border-amber-400 text-amber-300 group-hover:bg-amber-600 group-hover:text-white"
                        }`}
                      >
                        {hub.activeDispatches}
                      </div>
                    </div>

                    <div className="absolute top-6 left-1/2 -translate-x-1/2 whitespace-nowrap px-1.5 py-0.5 rounded bg-slate-950/90 border border-slate-800 text-[10px] font-semibold text-slate-200 pointer-events-none group-hover:border-amber-500/50">
                      {hub.name}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400 z-10 pt-2 border-t border-slate-800">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400" /> Number inside marker = active consignments
              </span>
              <span>Coordinates synced with carrier linehaul radar</span>
            </div>
          </div>

          {/* Selected Cluster Details Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 flex flex-col justify-between">
            {selectedHub ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 uppercase font-semibold">
                      {selectedHub.giTag}
                    </span>
                    <h3 className="text-base font-bold text-white mt-1">
                      {selectedHub.name}
                    </h3>
                    <p className="text-xs text-slate-400">{selectedHub.state}</p>
                  </div>
                  <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-amber-400">
                    <Store className="w-5 h-5" />
                  </div>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <span className="text-slate-400">Artisan Heritage Cluster:</span>
                    <div className="font-semibold text-white mt-0.5">
                      {selectedHub.artisanCluster}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg">
                      <div className="text-[11px] text-slate-400">Live Dispatches</div>
                      <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                        {selectedHub.activeDispatches} Parcels
                      </div>
                    </div>

                    <div className="bg-slate-950 border border-slate-800 p-3 rounded-lg">
                      <div className="text-[11px] text-slate-400">Gross Shipped</div>
                      <div className="text-base font-bold font-mono text-white mt-0.5">
                        {formatCurrency(selectedHub.todayGmvCents)}
                      </div>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
                    <div className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                      Active Courier Linehauls
                    </div>
                    <div className="space-y-1 font-mono text-[11px]">
                      <div className="flex justify-between text-slate-300">
                        <span>Blue Dart Express:</span>
                        <span className="text-amber-400">Air Priority (AWB #BD-883)</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span>Delhivery Surface:</span>
                        <span className="text-sky-400">Linehaul #441</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400 text-xs">
                Select an artisan craft hub on the map to inspect live dispatches.
              </div>
            )}

            <div className="pt-4 border-t border-slate-800 flex items-center justify-between text-xs">
              <span className="text-slate-400">Carrier API: Blue Dart &amp; Delhivery</span>
              <span className="text-emerald-400 font-mono flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Live Synced
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
