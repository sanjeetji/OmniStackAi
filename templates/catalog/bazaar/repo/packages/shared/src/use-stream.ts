"use client";

/** React hook for real-time Server-Sent Events (SSE). */

import { useEffect, useRef, useState } from "react";

export interface StreamEvent {
  type: string;
  payload: Record<string, any>;
  timestamp: string;
}

export function useStream(options: {
  baseUrl?: string;
  token?: string | null;
  onEvent?: (event: StreamEvent) => void;
  enabled?: boolean;
} = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Same resolution order as the API client, so the stream follows the API wherever it is served.
  const baseUrl =
    options.baseUrl ||
    (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
    (typeof window !== "undefined" ? (window as any).__BAZAAR_API_URL__ : null) ||
    "http://127.0.0.1:4000";

  const enabled = options.enabled !== false;

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;

    const token =
      options.token ??
      (typeof localStorage !== "undefined" ? localStorage.getItem("bazaar_token") : null);

    const streamUrl = `${baseUrl}/api/stream${token ? `?token=${encodeURIComponent(token)}` : ""}`;
    let es: EventSource;
    try {
      es = new EventSource(streamUrl);
      eventSourceRef.current = es;
    } catch {
      return;
    }

    es.addEventListener("open", () => {
      setIsConnected(true);
    });

    es.addEventListener("error", () => {
      setIsConnected(false);
    });

    const handleAnyEvent = (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data);
        const item: StreamEvent = {
          type: event.type,
          payload: parsed.payload || parsed,
          timestamp: parsed.timestamp || new Date().toISOString(),
        };
        setEvents((prev) => [item, ...prev.slice(0, 49)]);
        if (options.onEvent) {
          options.onEvent(item);
        }
      } catch {
        // Ignore parse errors on heartbeat pings
      }
    };

    es.addEventListener("connected", handleAnyEvent);
    es.addEventListener("order.created", handleAnyEvent);
    es.addEventListener("shipment.updated", handleAnyEvent);
    es.addEventListener("inventory.low", handleAnyEvent);
    es.addEventListener("return.requested", handleAnyEvent);
    es.addEventListener("ping", handleAnyEvent);

    return () => {
      es.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    };
  }, [baseUrl, options.token, enabled]);

  const clearEvents = () => setEvents([]);

  return { isConnected, events, clearEvents };
}
