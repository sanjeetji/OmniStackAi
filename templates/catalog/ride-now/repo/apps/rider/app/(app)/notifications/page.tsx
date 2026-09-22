"use client";

import { useEffect, useState } from "react";
import { Bell, CarFront, LifeBuoy, TicketPercent, Wallet } from "lucide-react";
import { relativeTime, type Notification } from "@ridenow/shared";
import { AppShell } from "@/components/app-shell";
import { Button, Card, EmptyState, PageHeader, Skeleton, cx } from "@/components/ui";
import { api } from "@/lib/api";

const ICON: Record<string, typeof Bell> = { trip: CarFront, wallet: Wallet, support: LifeBuoy, promo: TicketPercent };

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
    <AppShell>
      <PageHeader
        title="Notifications"
        action={unread > 0 ? (
          <Button variant="outline" size="sm" onClick={async () => {
            await api.post("/support/notifications/read");
            setUnread(0);
            setItems((current) => current?.map((n) => ({ ...n, read_at: n.read_at ?? new Date().toISOString() })) ?? null);
          }}>Mark all as read</Button>
        ) : undefined}
      />
      {items === null ? (
        <div className="grid gap-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-16" />)}</div>
      ) : items.length === 0 ? (
        <Card><EmptyState icon={<Bell className="size-6" />} title="You're all caught up" body="Ride updates, receipts and offers will appear here." /></Card>
      ) : (
        <Card className="divide-y divide-line">
          {items.map((item) => {
            const Icon = ICON[item.kind] ?? Bell;
            return (
              <div key={item.id} className={cx("flex gap-3 px-5 py-4", !item.read_at && "bg-amber-soft/40")}>
                <span className="grid size-10 shrink-0 place-items-center rounded-full bg-black/5"><Icon className="size-4" aria-hidden="true" /></span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{item.title}</p>
                  {item.body ? <p className="text-sm text-muted">{item.body}</p> : null}
                </div>
                <span className="shrink-0 text-xs text-muted">{relativeTime(item.created_at)}</span>
              </div>
            );
          })}
        </Card>
      )}
    </AppShell>
  );
}
