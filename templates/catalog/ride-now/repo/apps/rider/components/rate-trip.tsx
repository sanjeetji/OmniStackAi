"use client";

import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { ApiError } from "@ridenow/shared";
import { api } from "@/lib/api";
import { Alert, Button, Stars, cx } from "./ui";

const GOOD = ["Clean vehicle", "Safe driving", "Polite", "On time", "Knew the route", "Great music"];
const BAD = ["Late pickup", "Rash driving", "Took a longer route", "AC not working", "Unprofessional"];

export function RateTrip({ tripId, driverName, onRated }: { tripId: string; driverName: string; onRated: (stars: number) => void }) {
  const [stars, setStars] = useState(0);
  const [tags, setTags] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const options = stars >= 4 ? GOOD : stars > 0 ? BAD : [];

  if (done) {
    return (
      <p className="flex items-center gap-2 font-semibold text-success">
        <CheckCircle2 className="size-5" aria-hidden="true" /> Thanks for rating {driverName.split(" ")[0]}.
      </p>
    );
  }
  return (
    <div className="grid gap-4">
      <div>
        <p className="font-bold">How was your ride with {driverName.split(" ")[0]}?</p>
        <div className="mt-2"><Stars value={stars} onChange={(n) => { setStars(n); setTags([]); }} size={34} /></div>
      </div>
      {options.length ? (
        <div className="flex flex-wrap gap-2">
          {options.map((tag) => (
            <button key={tag} type="button" aria-pressed={tags.includes(tag)} onClick={() => setTags(tags.includes(tag) ? tags.filter((t) => t !== tag) : [...tags, tag])} className={cx("rounded-full border px-3 py-1.5 text-sm font-semibold transition", tags.includes(tag) ? "border-ink bg-ink text-white" : "border-line hover:border-ink/40")}>
              {tag}
            </button>
          ))}
        </div>
      ) : null}
      {stars > 0 ? (
        <textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={500} rows={2} placeholder="Anything else? (optional)" className="rounded-2xl border border-line bg-white p-3 text-sm outline-none focus:border-ink" />
      ) : null}
      {error ? <Alert>{error}</Alert> : null}
      <Button
        disabled={!stars}
        busy={busy}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            await api.post(`/rider/trips/${tripId}/rate`, { stars, tags, comment });
            setDone(true);
            onRated(stars);
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Couldn't save your rating.");
          } finally {
            setBusy(false);
          }
        }}
      >
        Submit rating
      </Button>
    </div>
  );
}
