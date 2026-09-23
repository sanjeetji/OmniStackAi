"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { defaultApiClient, useStream } from "@careclinic/shared";
import { useApi, useInterval } from "../../lib/use-api";

/**
 * The waiting-room board. It runs on a television, so it is deliberately outside the console
 * chrome and outside the staff guard: /api/admin/queue-display is the one admin route the API
 * leaves public, and it returns first names and token numbers only.
 */
export default function QueueDisplay() {
  const [now, setNow] = useState<Date | null>(null);
  const [pulse, setPulse] = useState(0);
  const queue = useApi(() => defaultApiClient.getQueueDisplay(), [pulse]);

  useStream({ onEvent: () => setPulse((value) => value + 1) });
  useInterval(() => setNow(new Date()), 1000);
  useInterval(queue.refresh, 15000);

  useEffect(() => setNow(new Date()), []);

  const entries = queue.data?.activeQueue ?? [];
  const inConsult = entries.filter((entry) => entry.queue_status === "with_doctor");
  const waiting = entries.filter((entry) => entry.queue_status !== "with_doctor");

  return (
    <main className="min-h-screen bg-[#060d18] px-8 py-6 text-white">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-lg bg-[var(--color-signal-bright)] text-[16px] font-bold text-[#04232b]">
            CC
          </span>
          <div>
            <h1 className="text-[24px] font-semibold tracking-tight">CareClinic Indiranagar</h1>
            <p className="text-[13px] text-slate-400">Outpatient department · now serving</p>
          </div>
        </div>
        <div className="text-right">
          <p className="tabular text-[34px] font-semibold leading-none">
            {now ? now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true }) : "--:--"}
          </p>
          <p className="text-[13px] text-slate-400">
            {now ? now.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" }) : ""}
          </p>
        </div>
      </header>

      <section className="mt-6">
        <h2 className="text-[13px] font-semibold uppercase tracking-[0.18em] text-[var(--color-signal-bright)]">
          In consultation
        </h2>
        {inConsult.length === 0 ? (
          <p className="mt-3 text-[18px] text-slate-500">No consultation in progress.</p>
        ) : (
          <div className="mt-3 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {inConsult.map((entry, index) => (
              <article key={`${entry.token_number}-${index}`} className="rounded-2xl bg-[var(--color-signal-bright)] p-6 text-[#04232b]">
                <p className="text-[13px] font-bold uppercase tracking-[0.14em] opacity-70">Token</p>
                <p className="tabular text-[68px] font-bold leading-none">{entry.token_number ?? "—"}</p>
                <p className="mt-3 text-[20px] font-semibold">{entry.room_number ?? "Consultation room"}</p>
                <p className="text-[15px] opacity-80">{entry.doctor_name}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="mt-8">
        <h2 className="text-[13px] font-semibold uppercase tracking-[0.18em] text-slate-400">Waiting</h2>
        {waiting.length === 0 ? (
          <p className="mt-3 text-[18px] text-slate-500">Nobody is waiting. Please check in at the front desk.</p>
        ) : (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {waiting.map((entry, index) => (
              <article
                key={`${entry.token_number}-${index}`}
                className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/5 px-5 py-4"
              >
                <div className="min-w-0">
                  <p className="truncate text-[15px] font-semibold">{entry.room_number ?? "Room to be assigned"}</p>
                  <p className="truncate text-[13px] text-slate-400">{entry.doctor_name}</p>
                </div>
                <p className="tabular text-[38px] font-bold leading-none text-[var(--color-signal-bright)]">
                  {entry.token_number ?? "—"}
                </p>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4 text-[13px] text-slate-500">
        <p>Please wait for your token to appear above. Keep your prescription and reports with you.</p>
        <Link href="/" className="text-slate-400 underline-offset-2 hover:text-white hover:underline">
          Back to the console
        </Link>
      </footer>
    </main>
  );
}
