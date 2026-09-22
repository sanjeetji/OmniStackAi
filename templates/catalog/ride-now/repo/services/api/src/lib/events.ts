/**
 * In-process realtime hub for Server-Sent Events. Channels:
 *   user:<id>   one person's trip, offer, wallet and notification updates
 *   trip:<id>   everyone watching a trip (rider, driver, admin)
 *   admin       live operations feed
 * One API instance is enough for the template; swap in Postgres LISTEN/NOTIFY or Redis for several.
 */
export interface RealtimeEvent {
  type: string;
  data: unknown;
}

type Listener = (event: RealtimeEvent) => void;

class Hub {
  private listeners = new Map<string, Set<Listener>>();

  subscribe(channels: string[], listener: Listener): () => void {
    for (const channel of channels) {
      if (!this.listeners.has(channel)) this.listeners.set(channel, new Set());
      this.listeners.get(channel)!.add(listener);
    }
    return () => {
      for (const channel of channels) {
        const set = this.listeners.get(channel);
        set?.delete(listener);
        if (set && set.size === 0) this.listeners.delete(channel);
      }
    };
  }

  publish(channel: string, type: string, data: unknown): void {
    for (const listener of this.listeners.get(channel) ?? []) {
      try {
        listener({ type, data });
      } catch {
        // A broken stream must not affect other listeners.
      }
    }
  }

  listenerCount(): number {
    let total = 0;
    for (const set of this.listeners.values()) total += set.size;
    return total;
  }
}

export const hub = new Hub();
