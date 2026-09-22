"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Briefcase, Home, LocateFixed, MapPin, Search, Star, X } from "lucide-react";
import type { Place, Stop } from "@ridenow/shared";
import { api } from "@/lib/api";
import { cx } from "./ui";

const LABEL_ICON: Record<string, typeof Home> = { Home, Work: Briefcase };

/** A place field: saved places first, then city search; also "pick on the map". */
export function PlaceSearch({
  label,
  value,
  onChange,
  saved,
  tone,
  onPickOnMap,
  picking,
  autoFocus,
}: {
  label: string;
  value: Stop | null;
  onChange: (stop: Stop | null) => void;
  saved: Place[];
  tone: "pickup" | "drop";
  onPickOnMap: () => void;
  picking: boolean;
  autoFocus?: boolean;
}) {
  const [query, setQuery] = useState(value?.name ?? "");
  const [results, setResults] = useState<Place[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = useId();
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => setQuery(value?.name ?? ""), [value?.name]);

  useEffect(() => {
    if (!open) return;
    const handle = setTimeout(() => {
      api.get<{ places: Place[] }>(`/places/search?q=${encodeURIComponent(query === value?.name ? "" : query)}`)
        .then((r) => setResults(r.places))
        .catch(() => setResults([]));
    }, 180);
    return () => clearTimeout(handle);
  }, [query, open, value?.name]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const lowered = query.toLowerCase();
  const savedMatches = saved.filter((p) => !query || query === value?.name || p.name.toLowerCase().includes(lowered) || (p.label ?? "").toLowerCase().includes(lowered));
  const options = [...savedMatches.map((p) => ({ ...p, saved: true })), ...results.filter((r) => !savedMatches.some((s) => s.name === r.name)).map((p) => ({ ...p, saved: false }))].slice(0, 9);

  const choose = (place: Place) => {
    onChange({ name: place.name, lat: place.lat, lng: place.lng });
    setQuery(place.name);
    setOpen(false);
  };

  return (
    <div ref={boxRef} className="relative">
      <div className={cx("flex h-14 items-center gap-3 rounded-2xl border bg-white px-4 transition focus-within:border-ink focus-within:ring-4 focus-within:ring-amber/25", picking ? "border-amber ring-4 ring-amber/30" : "border-line")}>
        <span aria-hidden="true" className={cx("size-3 shrink-0", tone === "pickup" ? "rounded-full bg-success" : "bg-ink")} />
        <div className="min-w-0 flex-1">
          <label htmlFor={`${listId}-input`} className="block text-[11px] font-bold uppercase tracking-wide text-muted">{label}</label>
          <input
            id={`${listId}-input`}
            role="combobox"
            aria-expanded={open}
            aria-controls={listId}
            aria-autocomplete="list"
            autoFocus={autoFocus}
            value={query}
            placeholder={tone === "pickup" ? "Where from?" : "Where to?"}
            onFocus={() => setOpen(true)}
            onChange={(event) => {
              setQuery(event.target.value);
              setOpen(true);
              setActive(0);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") { event.preventDefault(); setActive((i) => Math.min(i + 1, options.length - 1)); }
              if (event.key === "ArrowUp") { event.preventDefault(); setActive((i) => Math.max(i - 1, 0)); }
              if (event.key === "Enter" && options[active]) { event.preventDefault(); choose(options[active]); }
              if (event.key === "Escape") setOpen(false);
            }}
            className="w-full truncate bg-transparent text-[15px] font-semibold outline-none placeholder:font-medium placeholder:text-muted/70"
          />
        </div>
        {value ? (
          <button type="button" aria-label={`Clear ${label.toLowerCase()}`} onClick={() => { onChange(null); setQuery(""); }} className="grid size-8 place-items-center rounded-full text-muted hover:bg-black/5">
            <X className="size-4" aria-hidden="true" />
          </button>
        ) : null}
        <button type="button" onClick={onPickOnMap} aria-pressed={picking} title="Pick on the map" className={cx("grid size-9 place-items-center rounded-full", picking ? "bg-amber text-ink" : "text-muted hover:bg-black/5")}>
          <LocateFixed className="size-4" aria-hidden="true" />
          <span className="sr-only">Pick {label.toLowerCase()} on the map</span>
        </button>
      </div>
      {open && options.length > 0 ? (
        <ul id={listId} role="listbox" className="rn-rise absolute inset-x-0 top-[calc(100%+6px)] z-30 max-h-80 overflow-auto rounded-2xl border border-line bg-white p-1.5 shadow-[var(--shadow-float)]">
          {options.map((place, index) => {
            const Icon = place.saved ? LABEL_ICON[place.label ?? ""] ?? Star : place.label === "Landmark" ? MapPin : Search;
            return (
              <li key={`${place.id}-${index}`} role="option" aria-selected={index === active}>
                <button type="button" onMouseEnter={() => setActive(index)} onClick={() => choose(place)} className={cx("flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left", index === active && "bg-black/5")}>
                  <span className={cx("grid size-9 shrink-0 place-items-center rounded-full", place.saved ? "bg-amber-soft text-amber-deep" : "bg-black/5 text-muted")}>
                    <Icon className="size-4" aria-hidden="true" />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold">{place.saved ? `${place.label} · ${place.name}` : place.name}</span>
                    <span className="block truncate text-xs text-muted">{place.address}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
