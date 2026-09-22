"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@ridenow/shared";
import { api } from "./api";

export interface Loaded<T> {
  data: T | null;
  error: string | null;
  /** True only for the first load; later reloads keep showing the previous data. */
  loading: boolean;
  reload: () => void;
  setData: (update: T | ((current: T | null) => T | null)) => void;
}

/** GET `path` (null skips) and keep the result; `reload()` refetches without blanking the page. */
export function useApi<T>(path: string | null): Loaded<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const [tick, setTick] = useState(0);
  const lastPath = useRef<string | null>(null);

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;
    if (lastPath.current !== path) {
      lastPath.current = path;
      setLoading(true);
    }
    api
      .get<T>(path)
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Couldn't load this page. Check that the API is running.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [path, tick]);

  const reload = useCallback(() => setTick((n) => n + 1), []);
  return { data, error, loading, reload, setData: setData as Loaded<T>["setData"] };
}

/** Call `fn` every `ms` while the tab is visible. */
export function useInterval(fn: () => void, ms: number): void {
  const latest = useRef(fn);
  latest.current = fn;
  useEffect(() => {
    const timer = setInterval(() => {
      if (typeof document === "undefined" || document.visibilityState === "visible") latest.current();
    }, ms);
    return () => clearInterval(timer);
  }, [ms]);
}

/** Turn a caught error into a message for the operator. */
export function errorText(err: unknown, fallback = "Something went wrong. Please try again."): string {
  return err instanceof ApiError ? err.message : fallback;
}
