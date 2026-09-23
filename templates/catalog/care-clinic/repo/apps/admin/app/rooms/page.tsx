"use client";

import { useState } from "react";
import Link from "next/link";
import { DoorOpen, PencilLine } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Badge, Button, DataState, ErrorNote, Stat, inputClass } from "../../components/ui";
import { useApi, useAction, useInterval } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { count, money, num } from "../../lib/format";

export default function RoomBoard() {
  const { pulse, prefs, notify } = useSession();
  const rooms = useApi(() => defaultApiClient.getRooms(), [pulse]);
  const { run, busy, error } = useAction();
  const [editing, setEditing] = useState<string | null>(null);
  const [roomValue, setRoomValue] = useState("");

  useInterval(rooms.refresh, prefs.refreshSeconds * 1000);

  const list = rooms.data?.rooms ?? [];
  const inUse = list.filter((room) => room.current_token !== null);
  const away = list.filter((room) => room.leave_reason);

  async function save(doctorId: string) {
    const ok = await run(() => defaultApiClient.assignRoom(doctorId, roomValue.trim()));
    if (ok) {
      notify({ title: "Chamber updated", detail: roomValue.trim(), tone: "good" });
      setEditing(null);
      rooms.refresh();
    }
  }

  return (
    <Shell title="Rooms" subtitle="Which chamber each doctor is in, and who is being seen right now">
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Chambers in use" value={`${inUse.length} of ${list.length}`} tone="signal" icon={<DoorOpen size={15} />} />
        <Stat label="Patients waiting" value={count(list.reduce((sum, room) => sum + num(room.waiting_now), 0))} hint="Across every chamber" />
        <Stat label="Doctors away today" value={away.length} tone={away.length ? "alert" : "plain"} hint="Recorded on the roster" />
      </div>

      <DataState state={rooms}>
        {(data) => (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {data.rooms.map((room) => {
              const busyNow = room.current_token !== null;
              return (
                <article
                  key={room.doctor_id}
                  className={
                    busyNow
                      ? "rounded-lg border border-cyan-200 bg-[var(--color-signal-soft)] p-4"
                      : "rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-4"
                  }
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-[13px] font-semibold text-[var(--color-ink)]">
                        {room.room_number ?? "No chamber assigned"}
                      </p>
                      <p className="truncate text-[12px] text-[var(--color-ink-muted)]">{room.doctor_name}</p>
                    </div>
                    {room.leave_reason ? (
                      <Badge tone="danger">On leave</Badge>
                    ) : busyNow ? (
                      <Badge tone="signal">In consult</Badge>
                    ) : room.on_duty ? (
                      <Badge tone="good">Free</Badge>
                    ) : (
                      <Badge>Off duty</Badge>
                    )}
                  </div>

                  <div className="mt-3 flex items-end justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]">
                        Now seeing
                      </p>
                      <p className="tabular text-[20px] font-semibold leading-tight text-[var(--color-ink)]">
                        {room.current_token !== null ? `Token ${room.current_token}` : "—"}
                      </p>
                      <p className="truncate text-[12px] text-[var(--color-ink-muted)]">
                        {room.current_patient ?? room.leave_reason ?? "Chamber free"}
                      </p>
                    </div>
                    <dl className="text-right text-[11.5px] text-[var(--color-ink-muted)]">
                      <div className="tabular">{count(room.booked_today)} booked</div>
                      <div className="tabular">{count(room.waiting_now)} waiting</div>
                      <div className="tabular">{money(room.consultation_fee_inr)}</div>
                    </dl>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--color-border)] pt-2.5">
                    {editing === room.doctor_id ? (
                      <>
                        <input
                          className={`${inputClass} flex-1`}
                          value={roomValue}
                          onChange={(event) => setRoomValue(event.target.value)}
                          placeholder="OPD Room 104"
                          autoFocus
                        />
                        <Button size="sm" disabled={busy || !roomValue.trim()} onClick={() => void save(room.doctor_id)}>
                          Save
                        </Button>
                        <Button size="sm" variant="quiet" onClick={() => setEditing(null)}>
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          size="sm"
                          variant="quiet"
                          onClick={() => {
                            setEditing(room.doctor_id);
                            setRoomValue(room.room_number ?? "");
                          }}
                        >
                          <PencilLine size={13} /> Reassign
                        </Button>
                        <Link
                          href={`/doctors/${room.doctor_id}/schedule`}
                          className="text-[12px] font-semibold text-[var(--color-signal)] hover:underline"
                        >
                          Roster
                        </Link>
                      </>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </DataState>
    </Shell>
  );
}
