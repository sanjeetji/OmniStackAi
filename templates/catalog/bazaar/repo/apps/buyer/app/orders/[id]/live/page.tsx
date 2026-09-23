"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useStream, formatCurrency, formatDate } from "@bazaar/shared";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function OrderLiveTrackingPage({ params }: PageProps) {
  const { id } = use(params);
  const { isConnected, events, clearEvents } = useStream();

  // Simulated live telemetry state
  const [telemetry, setTelemetry] = useState({
    originCity: "Jaipur, Rajasthan",
    originCoords: "26.9124° N, 75.7873° E",
    currentLocation: "National Highway 48, Near Vadodara Hub",
    currentCoords: "22.3072° N, 73.1812° E",
    destinationCity: "Indiranagar, Bengaluru, Karnataka",
    destinationCoords: "12.9784° N, 77.6408° E",
    transitProgress: 68,
    speedKmh: 72,
    etaMinutes: 240,
    containerTempC: 22.4,
    lastPing: new Date().toLocaleTimeString(),
  });

  // Periodically update simulated vehicle location
  useEffect(() => {
    const timer = setInterval(() => {
      setTelemetry((prev) => ({
        ...prev,
        transitProgress: Math.min(99, prev.transitProgress + (Math.random() > 0.5 ? 1 : 0)),
        speedKmh: Math.floor(65 + Math.random() * 15),
        etaMinutes: Math.max(15, prev.etaMinutes - 1),
        containerTempC: +(22.0 + Math.random() * 0.8).toFixed(1),
        lastPing: new Date().toLocaleTimeString(),
      }));
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-stone-500 mb-6">
        <Link href="/orders" className="hover:text-amber-800">
          My Orders
        </Link>
        <span>&rsaquo;</span>
        <Link href={`/orders/${id}`} className="hover:text-amber-800 font-mono">
          #{id}
        </Link>
        <span>&rsaquo;</span>
        <span className="font-semibold text-stone-800">Live Telemetry & Stream</span>
      </nav>

      {/* Top Banner with SSE Connection Pill */}
      <div className="bg-stone-900 text-white rounded-2xl p-6 mb-8 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl">
        <div>
          <div className="flex items-center gap-3">
            <span
              className={`w-3 h-3 rounded-full ${
                isConnected ? "bg-emerald-400 animate-ping" : "bg-amber-400"
              }`}
            ></span>
            <span className="text-xs uppercase font-bold tracking-widest text-amber-400">
              {isConnected ? "Real-Time SSE Connected" : "Connecting to Event Gateway..."}
            </span>
          </div>
          <h1 className="text-3xl font-serif font-bold mt-1">Live Consignment Radar</h1>
          <p className="text-stone-400 text-sm mt-1">
            Tracking GPS telemetry and artisan handoff checkpoints in real-time.
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="bg-stone-800 px-4 py-2.5 rounded-xl border border-stone-700 text-right">
            <span className="text-xs text-stone-400 block">Estimated Arrival</span>
            <span className="text-lg font-bold text-amber-300">
              ~{Math.floor(telemetry.etaMinutes / 60)}h {telemetry.etaMinutes % 60}m
            </span>
          </div>
          <Link
            href={`/orders/${id}`}
            className="px-4 py-2.5 bg-amber-700 hover:bg-amber-600 text-white rounded-xl text-xs font-semibold transition"
          >
            Order Details &rarr;
          </Link>
        </div>
      </div>

      {/* Map & Live Metrics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* Visual Map / Route Canvas (2 cols) */}
        <div className="lg:col-span-2 bg-stone-950 rounded-2xl p-6 text-white border border-stone-800 relative overflow-hidden flex flex-col justify-between min-h-[440px]">
          {/* Subtle Map Grid Pattern */}
          <div
            className="absolute inset-0 opacity-15 pointer-events-none"
            style={{
              backgroundImage:
                "radial-gradient(#d97706 1px, transparent 1px), radial-gradient(#d97706 1px, #0c0a09 1px)",
              backgroundSize: "24px 24px",
              backgroundPosition: "0 0, 12px 12px",
            }}
          ></div>

          {/* Map Top Status */}
          <div className="relative z-10 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs">
              <span className="px-2.5 py-1 bg-amber-950/80 border border-amber-600/50 rounded-lg text-amber-300 font-mono">
                ROUTE: JAIPUR &rarr; BENGALURU
              </span>
              <span className="px-2.5 py-1 bg-stone-800 rounded-lg text-stone-300 font-mono">
                NH-48 CORRIDOR
              </span>
            </div>
            <span className="text-xs font-mono text-stone-400">
              Ping: {telemetry.lastPing}
            </span>
          </div>

          {/* Visual Route Nodes */}
          <div className="relative z-10 py-12 px-4">
            <div className="relative">
              {/* Route Line */}
              <div className="h-1.5 w-full bg-stone-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-500 via-amber-400 to-emerald-400 transition-all duration-1000"
                  style={{ width: `${telemetry.transitProgress}%` }}
                ></div>
              </div>

              {/* Waypoints */}
              <div className="flex justify-between items-center -mt-3.5">
                {/* Node 1: Origin */}
                <div className="flex flex-col items-center">
                  <div className="w-6 h-6 rounded-full bg-amber-500 text-stone-950 font-bold text-xs flex items-center justify-center ring-4 ring-amber-950">
                    A
                  </div>
                  <span className="text-xs font-bold text-amber-400 mt-2">Jaipur Atelier</span>
                  <span className="text-[10px] text-stone-400 font-mono">Craftsman Dispatch</span>
                </div>

                {/* Node 2: Air Hub */}
                <div className="flex flex-col items-center">
                  <div className="w-6 h-6 rounded-full bg-amber-400 text-stone-950 font-bold text-xs flex items-center justify-center ring-4 ring-amber-950">
                    B
                  </div>
                  <span className="text-xs font-medium text-stone-300 mt-2">Delhi Hub</span>
                  <span className="text-[10px] text-stone-400 font-mono">Sorted & Scanned</span>
                </div>

                {/* Node 3: Current Transit Van */}
                <div className="flex flex-col items-center">
                  <div className="w-8 h-8 rounded-full bg-emerald-400 text-stone-950 font-bold text-sm flex items-center justify-center ring-4 ring-emerald-950 animate-bounce">
                    🚚
                  </div>
                  <span className="text-xs font-bold text-emerald-300 mt-1">In Transit</span>
                  <span className="text-[10px] text-emerald-400 font-mono">
                    {telemetry.speedKmh} km/h
                  </span>
                </div>

                {/* Node 4: Destination */}
                <div className="flex flex-col items-center">
                  <div className="w-6 h-6 rounded-full bg-stone-700 text-stone-300 font-bold text-xs flex items-center justify-center ring-4 ring-stone-900">
                    C
                  </div>
                  <span className="text-xs font-medium text-stone-400 mt-2">Bengaluru</span>
                  <span className="text-[10px] text-stone-500 font-mono">Customer Doorstep</span>
                </div>
              </div>
            </div>
          </div>

          {/* Telemetry Readouts Bottom Bar */}
          <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-3 bg-stone-900/90 p-4 rounded-xl border border-stone-800 text-xs">
            <div>
              <span className="text-stone-400 block text-[11px]">Current Location</span>
              <strong className="text-stone-200">{telemetry.currentLocation}</strong>
            </div>
            <div>
              <span className="text-stone-400 block text-[11px]">Coordinates</span>
              <span className="font-mono text-amber-300">{telemetry.currentCoords}</span>
            </div>
            <div>
              <span className="text-stone-400 block text-[11px]">Vehicle Speed</span>
              <strong className="text-emerald-400 font-mono">{telemetry.speedKmh} km/h</strong>
            </div>
            <div>
              <span className="text-stone-400 block text-[11px]">Cargo Temp</span>
              <strong className="text-stone-200 font-mono">{telemetry.containerTempC} °C</strong>
            </div>
          </div>
        </div>

        {/* Live SSE Event Stream Console (1 col) */}
        <div className="bg-white rounded-2xl p-6 border border-stone-200 flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-stone-100 mb-4">
              <div>
                <h3 className="text-sm font-bold text-stone-900">Server-Sent Events</h3>
                <p className="text-xs text-stone-500">Live feed from Bazaar gateway</p>
              </div>
              <button
                onClick={clearEvents}
                className="text-xs text-stone-500 hover:text-stone-800 underline"
              >
                Clear
              </button>
            </div>

            {/* Event List */}
            <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1 text-xs">
              {events.length === 0 ? (
                <div className="text-center py-10 text-stone-400">
                  <span className="text-2xl block mb-2">📡</span>
                  Listening for stream pulses...
                </div>
              ) : (
                events.map((evt: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-stone-50 rounded-lg border border-stone-200 font-mono"
                  >
                    <div className="flex items-center justify-between text-[11px] text-amber-800 font-semibold mb-1">
                      <span>{evt.type}</span>
                      <span className="text-stone-400">
                        {new Date(evt.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <pre className="text-[10px] text-stone-600 whitespace-pre-wrap break-all">
                      {JSON.stringify(evt.payload, null, 2)}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-stone-100 mt-4 text-center">
            <p className="text-[11px] text-stone-400">
              Encrypted channel &bull; SSE Keepalive: 25s &bull; Auto-reconnect enabled
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
