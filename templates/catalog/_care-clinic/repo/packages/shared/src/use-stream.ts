"use client";

/** React hook for real-time Server-Sent Events (SSE) in CareClinic. */

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

  const baseUrl =
    options.baseUrl ||
    (typeof window !== "undefined"
      ? (window as any).__CARECLINIC_API_URL__ || "http://127.0.0.1:4000"
      : "http://127.0.0.1:4000");

  const enabled = options.enabled !== false;

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;

    const token =
      options.token ??
      (typeof localStorage !== "undefined" ? localStorage.getItem("careclinic_token") : null);

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
        // Ignore parse errors on heartbeat
      }
    };

    es.addEventListener("connected", handleAnyEvent);
    es.addEventListener("appointment_booked", handleAnyEvent);
    es.addEventListener("queue_updated", handleAnyEvent);
    es.addEventListener("consultation_started", handleAnyEvent);
    es.addEventListener("prescription_issued", handleAnyEvent);
    es.addEventListener("payment_received", handleAnyEvent);
    es.addEventListener("ping", handleAnyEvent);

    return () => {
      es.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    };
  }, [enabled, baseUrl, options.token]);

  return { isConnected, events };
}
