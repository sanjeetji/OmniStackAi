"use client";

import { useEffect, useRef, useState } from "react";
import type { PreviewStatus } from "@/lib/control-plane";
import { RefreshIcon, StopIcon, WarningIcon } from "./studio-icons";

const POLL_INTERVAL_MS = 5000;

type ErrorBody = { error?: string };

async function postJSON(path: string): Promise<{ status: number; body: PreviewStatus | ErrorBody }> {
  const response = await fetch(path, { method: "POST" });
  const body = (await response.json().catch(() => ({}))) as PreviewStatus | ErrorBody;
  return { status: response.status, body };
}

export function StudioPreview({
  buildId,
  previewVersion,
}: {
  buildId: string | null;
  previewVersion: number;
}) {
  const [status, setStatus] = useState<PreviewStatus | null>(null);
  // starting/elapsedMs/fetchError travel together as one state value so the effect below only
  // ever needs one setState call at its start, not several cascading ones.
  const [phase, setPhase] = useState<{ starting: boolean; elapsedMs: number; fetchError: string | null }>({
    starting: false,
    elapsedMs: 0,
    fetchError: null,
  });
  const [disabled, setDisabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const startedAtRef = useRef<number | null>(null);

  // Start (or re-start) the preview for this build whenever buildId first becomes real, or
  // previewVersion bumps (the parent bumps it after every successful edit - _edit() never restarts
  // the preview on its own, unlike _build(), so this call is what keeps the iframe fresh).
  useEffect(() => {
    if (!buildId) {
      return;
    }
    let cancelled = false;
    startedAtRef.current = Date.now();
    (async () => {
      setPhase({ starting: true, elapsedMs: 0, fetchError: null });
      try {
        const { status: httpStatus, body } = await postJSON(
          `/api/jobs/build/${encodeURIComponent(buildId)}/preview`,
        );
        if (cancelled) return;
        if (httpStatus === 404) {
          setDisabled(true);
          setStatus(null);
          return;
        }
        setDisabled(false);
        setStatus(body as PreviewStatus);
      } catch {
        if (!cancelled) setPhase((p) => ({ ...p, fetchError: "could not reach the server" }));
      } finally {
        if (!cancelled) setPhase((p) => ({ ...p, starting: false }));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [buildId, previewVersion]);

  // Real elapsed time while starting - cold starts confirmed live up to ~45s during R-478.
  useEffect(() => {
    if (!phase.starting) return;
    const tick = setInterval(() => {
      setPhase((p) => ({ ...p, elapsedMs: Date.now() - (startedAtRef.current ?? Date.now()) }));
    }, 500);
    return () => clearInterval(tick);
  }, [phase.starting]);

  // Crash detection, not progress-watching: preview start is synchronous, so the only thing worth
  // polling for is a "ready" preview whose subprocess died on its own since the last check.
  useEffect(() => {
    if (!buildId || disabled || status?.status !== "ready") return;
    const interval = setInterval(async () => {
      try {
        const response = await fetch("/api/preview");
        if (response.status === 404) {
          setDisabled(true);
          return;
        }
        const body = (await response.json().catch(() => null)) as PreviewStatus | null;
        if (body) setStatus(body);
      } catch {
        // A transient poll failure isn't worth surfacing - the next tick retries.
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [buildId, disabled, status?.status]);

  async function handleRestart() {
    setBusy(true);
    try {
      const { status: httpStatus, body } = await postJSON("/api/preview/restart");
      if (httpStatus === 404) {
        setDisabled(true);
      } else {
        setStatus(body as PreviewStatus);
      }
    } catch {
      setPhase((p) => ({ ...p, fetchError: "could not reach the server" }));
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    try {
      const { status: httpStatus, body } = await postJSON("/api/preview/stop");
      if (httpStatus === 404) {
        setDisabled(true);
      } else {
        setStatus(body as PreviewStatus);
      }
    } catch {
      setPhase((p) => ({ ...p, fetchError: "could not reach the server" }));
    } finally {
      setBusy(false);
    }
  }

  if (!buildId) return null;

  if (disabled) {
    return (
      <section className="panel preview-disabled">
        <WarningIcon />
        <span>
          Live preview isn&apos;t running — start it with{" "}
          <code>task agent-engine:studio:preview</code>.
        </span>
      </section>
    );
  }

  if (phase.fetchError) {
    return (
      <section className="panel preview-disabled">
        <div className="error-banner">{phase.fetchError}</div>
      </section>
    );
  }

  if (phase.starting) {
    return (
      <section className="panel preview-starting">
        <span className="spinner" /> Starting preview… ({Math.round(phase.elapsedMs / 1000)}s)
      </section>
    );
  }

  if (!status || status.status === "idle") {
    return null;
  }

  if (status.status === "ready" && status.web_url) {
    return (
      <section className="panel preview-panel">
        <div className="preview-header">
          <span className="badge on">Live</span>
          <a href={status.web_url} target="_blank" rel="noreferrer" className="mono preview-url">
            {status.web_url}
          </a>
          <div className="preview-actions">
            <button type="button" className="button button--secondary" onClick={handleRestart} disabled={busy}>
              <RefreshIcon width={14} height={14} /> Restart
            </button>
            <button type="button" className="button button--secondary" onClick={handleStop} disabled={busy}>
              <StopIcon width={14} height={14} /> Stop
            </button>
          </div>
        </div>
        <iframe src={status.web_url} className="preview-frame" title="Live preview" />
      </section>
    );
  }

  return (
    <section className="panel preview-disabled">
      <WarningIcon />
      <span>{status.message}</span>
      <button type="button" className="button button--secondary" onClick={handleRestart} disabled={busy}>
        <RefreshIcon width={14} height={14} /> Restart
      </button>
    </section>
  );
}
