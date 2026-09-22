"use client";

import { useEffect, useState } from "react";
import { Briefcase, Home, MapPin, Plus, Star, Trash2 } from "lucide-react";
import { ApiError, type Place, type Stop } from "@ridenow/shared";
import { CityMap } from "@ridenow/shared/map";
import { AppShell } from "@/components/app-shell";
import { PlaceSearch } from "@/components/place-search";
import { Alert, Button, Card, EmptyState, Input, PageHeader, Sheet, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";

const ICON: Record<string, typeof Home> = { Home, Work: Briefcase };

export default function PlacesPage() {
  const [places, setPlaces] = useState<Place[] | null>(null);
  const [adding, setAdding] = useState(false);
  const load = () => api.get<{ places: Place[] }>("/rider/places").then((r) => setPlaces(r.places)).catch(() => setPlaces([]));
  useEffect(() => void load(), []);

  return (
    <AppShell>
      <PageHeader title="Saved places" subtitle="One tap to your usual spots." action={<Button onClick={() => setAdding(true)}><Plus className="size-4" aria-hidden="true" /> Add place</Button>} />
      {places === null ? (
        <div className="grid gap-3">{[0, 1].map((i) => <Skeleton key={i} className="h-20" />)}</div>
      ) : places.length === 0 ? (
        <Card><EmptyState icon={<MapPin className="size-6" />} title="No saved places" body="Save Home and Work to book faster." action={<Button onClick={() => setAdding(true)}>Add your first place</Button>} /></Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {places.map((place) => {
            const Icon = ICON[place.label ?? ""] ?? Star;
            return (
              <Card key={place.id} as="article" className="flex items-center gap-4 p-4">
                <span className="grid size-12 place-items-center rounded-2xl bg-amber-soft text-amber-deep"><Icon className="size-5" aria-hidden="true" /></span>
                <div className="min-w-0 flex-1">
                  <p className="font-bold">{place.label}</p>
                  <p className="truncate text-sm text-muted">{place.address || place.name}</p>
                </div>
                <button
                  type="button"
                  aria-label={`Delete ${place.label}`}
                  onClick={async () => {
                    await api.del(`/rider/places/${place.id}`);
                    setPlaces(places.filter((p) => p.id !== place.id));
                  }}
                  className="grid size-10 place-items-center rounded-full text-muted hover:bg-danger-soft hover:text-danger"
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                </button>
              </Card>
            );
          })}
        </div>
      )}
      <AddPlace open={adding} onClose={() => setAdding(false)} onSaved={() => { setAdding(false); void load(); }} />
    </AppShell>
  );
}

function AddPlace({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const [label, setLabel] = useState("Home");
  const [stop, setStop] = useState<Stop | null>(null);
  const [address, setAddress] = useState("");
  const [picking, setPicking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <Sheet open={open} onClose={onClose} title="Save a place">
      <div className="grid gap-4">
        <div className="flex flex-wrap gap-2">
          {["Home", "Work", "Gym", "Parents"].map((value) => (
            <button key={value} type="button" aria-pressed={label === value} onClick={() => setLabel(value)} className={`rounded-full border px-3 py-1.5 text-sm font-semibold ${label === value ? "border-ink bg-ink text-white" : "border-line"}`}>{value}</button>
          ))}
        </div>
        <Input label="Label" value={label} onChange={(e) => setLabel(e.target.value)} maxLength={30} />
        <PlaceSearch label="Location" tone="pickup" value={stop} onChange={setStop} saved={[]} picking={picking} onPickOnMap={() => setPicking(!picking)} />
        {picking ? (
          <div className="h-56 overflow-hidden rounded-2xl ring-1 ring-line">
            <CityMap
              markers={stop ? [{ id: "s", kind: "pickup", ...stop }] : []}
              focus={stop ? [stop] : undefined}
              onPick={(point) => { setStop({ name: `Pinned location (${point.lat.toFixed(4)}, ${point.lng.toFixed(4)})`, ...point }); setPicking(false); }}
              ariaLabel="Tap to choose a location"
            />
          </div>
        ) : null}
        <Input label="Address details (optional)" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Flat, building, landmark" maxLength={200} />
        {error ? <Alert>{error}</Alert> : null}
        <Button
          size="lg"
          disabled={!stop || !label.trim()}
          busy={busy}
          onClick={async () => {
            if (!stop) return;
            setBusy(true);
            setError(null);
            try {
              await api.post("/rider/places", { label: label.trim(), ...stop, address: address || stop.name });
              setStop(null);
              setAddress("");
              onSaved();
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Couldn't save the place.");
            } finally {
              setBusy(false);
            }
          }}
        >
          Save place
        </Button>
      </div>
    </Sheet>
  );
}
