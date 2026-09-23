"use client";

/** React hook for real-time Server-Sent Events (SSE) in CareClinic. */

import { useEffect, useRef, useState } from "react";

export interface StreamEvent {
  type: string;
  payload: Record<string, any>;
  timestamp: string;
}

/** Every event the API broadcasts, plus the connection and heartbeat frames. */
export const STREAM_EVENTS = [
  "connected",
  "ping",
  "appointment_booked",
  "appointment_cancelled",
  "queue_updated",
  "token_called",
  "consultation_started",
  "consultation_completed",
  "prescription_issued",
  "lab_updated",
  "schedule_updated",
  "payment_received",
  "telehealth_participant_joined",
  "telehealth_call_ended",
] as const;

export type StreamEventName = (typeof STREAM_EVENTS)[number];

export function useStream(options: {
  baseUrl?: string;
  token?: string | null;
  onEvent?: (event: StreamEvent) => void;
  enabled?: boolean;
} = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Same resolution order as the API client, so the stream follows the API wherever it is served
  // (the OmniStack preview gives every app its own port).
  const baseUrl =
    options.baseUrl ||
    (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
    (typeof window !== "undefined" ? (window as any).__CARECLINIC_API_URL__ : null) ||
    "http://127.0.0.1:4000";

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

    for (const name of STREAM_EVENTS) {
      es.addEventListener(name, handleAnyEvent);
    }

    return () => {
      es.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    };
  }, [enabled, baseUrl, options.token]);

  return { isConnected, events };
}
