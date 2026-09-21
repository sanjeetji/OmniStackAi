"use client";

import { useEffect, useRef } from "react";
import type { ApiClient } from "./api.ts";

export type StreamHandlers = Partial<Record<string, (data: any) => void>>;

/**
 * Subscribe to the API's Server-Sent Events while the component is mounted. Reconnects with
 * backoff; each reconnect uses the current (possibly refreshed) access token.
 */
export function useStream(api: ApiClient, handlers: StreamHandlers, enabled = true): void {
  const latest = useRef(handlers);
  latest.current = handlers;

  useEffect(() => {
    if (!enabled || typeof window === "undefined") return;
    let source: EventSource | null = null;
    let stopped = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const events = ["trip.updated", "offer.new", "offer.closed", "driver.location", "driver.status", "wallet.updated", "notification", "ticket.created", "ticket.updated", "payout.requested", "zone.updated"];

    const connect = () => {
      const url = api.streamUrl();
      if (!url || stopped) return;
      source = new EventSource(url);
      source.addEventListener("ready", () => {
        attempt = 0;
      });
      for (const name of events) {
        source.addEventListener(name, (event) => {
          try {
            latest.current[name]?.(JSON.parse((event as MessageEvent).data));
          } catch {
            // Ignore a malformed frame.
          }
        });
      }
      source.onerror = () => {
        source?.close();
        if (stopped) return;
        attempt += 1;
        timer = setTimeout(connect, Math.min(15_000, 1_000 * 2 ** Math.min(attempt, 4)));
      };
    };
    connect();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      source?.close();
    };
  }, [api, enabled]);
}
