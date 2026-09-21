"use client";

import { useEffect, useState } from "react";
import { Bell, CarFront, FileCheck2, IndianRupee, Landmark, LifeBuoy, Wallet } from "lucide-react";
import { relativeTime, type Notification } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Button, Empty, Loading, Panel, cx } from "@/components/ui";
import { api } from "@/lib/api";

const ICON: Record<string, typeof Bell> = { trip: CarFront, wallet: Wallet, earning: IndianRupee, payout: Landmark, support: LifeBuoy, account: FileCheck2 };

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[] | null>(null);
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    api.get<{ notifications: Notification[]; unread: number }>("/support/notifications?limit=50").then((r) => {
      setItems(r.notifications);
      setUnread(r.unread);
    }).catch(() => setItems([]));
  }, []);

  return (
    <Shell
      title="Notifications"
      action={unread > 0 ? (
        <Button size="sm" variant="outline" onClick={async () => {
          await api.post("/support/notifications/read");
          setUnread(0);
          setItems((current) => current?.map((n) => ({ ...n, read_at: n.read_at ?? new Date().toISOString() })) ?? null);
        }}>Mark all read</Button>
      ) : undefined}
    >
      {items === null ? <Loading /> : items.length === 0 ? (
        <Panel><Empty icon={<Bell className="size-6" />} title="You're all caught up" body="Ride requests you missed, payouts and document updates will appear here." /></Panel>
      ) : (
        <Panel className="divide-y divide-line/60">
          {items.map((item) => {
            const Icon = ICON[item.kind] ?? Bell;
            return (
              <div key={item.id} className={cx("flex gap-3 px-4 py-3.5", !item.read_at && "bg-go-soft/40")}>
                <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-raised"><Icon className="size-4" aria-hidden="true" /></span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{item.title}</p>
                  {item.body ? <p className="text-sm text-fg-muted">{item.body}</p> : null}
                </div>
                <span className="shrink-0 text-xs text-fg-muted">{relativeTime(item.created_at)}</span>
              </div>
            );
          })}
        </Panel>
      )}
    </Shell>
  );
}
