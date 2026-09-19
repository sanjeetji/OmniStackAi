"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type {
  BuildEditResponse,
  BuildFileTreeResponse,
  BuildJobResponse,
  BuildTurnsResponse,
  ChatTurn,
} from "@/lib/control-plane";
import { CreditIcon, SendIcon } from "./studio-icons";
import { StudioTabs } from "./studio-tabs";
import { StudioWorkspace, type WorkspaceSnapshot } from "./studio-workspace";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: number;
  kind: "plain" | "error";
}

type ErrorBody = { error?: string };

let messageCounter = 0;
function nextMessageId(): string {
  messageCounter += 1;
  return `m${Date.now()}-${messageCounter}`;
}

export default function StudioChat({ initialCreditBalance }: { initialCreditBalance: number }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlBuildId = searchParams.get("build");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [buildId, setBuildId] = useState<string | null>(urlBuildId);
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot | null>(null);
  // Bumped after every successful edit so <StudioPreview> re-previews this build - _edit() never
  // restarts the preview on its own, unlike _build() (which StudioPreview already re-previews for
  // via its own buildId-change effect, so no bump is needed on a fresh build).
  const [previewVersion, setPreviewVersion] = useState(0);
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // R-485: ticks up live as generating_ir deltas arrive during a streaming build - the visible
  // proof of real incremental progress, reset to 0 whenever a new build starts. Not used for
  // edits (which stay non-streaming, per R-484's own scope boundary).
  const [streamChars, setStreamChars] = useState(0);
  const [hydrating, setHydrating] = useState(Boolean(urlBuildId));
  const [creditBalance, setCreditBalance] = useState(initialCreditBalance);
  const threadRef = useRef<HTMLDivElement | null>(null);
  const hydratedFor = useRef<string | null>(null);

  useEffect(() => {
    if (!urlBuildId || hydratedFor.current === urlBuildId) {
      setHydrating(false);
      return;
    }
    hydratedFor.current = urlBuildId;
    let cancelled = false;
    const errorMessage = (text: string): ChatMessage => ({
      id: nextMessageId(),
      role: "assistant",
      text,
      createdAt: Date.now() / 1000,
      kind: "error",
    });
    (async () => {
      try {
        const response = await fetch(`/api/jobs/build/${encodeURIComponent(urlBuildId)}/turns`);
        const body = (await response.json().catch(() => ({}))) as Partial<BuildTurnsResponse> &
          ErrorBody;
        if (cancelled) return;
        if (!response.ok) {
          // A real, mapped error here (401/502) - not the "unknown build" case, which the
          // agent-engine reports as an empty turns list rather than an error (see the R-477 task
          // contract's Finding). Surface it, but keep buildId - the user can still try sending a
          // message, which will get the real, authoritative answer.
          setMessages((prev) => [...prev, errorMessage(body.error ?? "could not load this build's history")]);
          return;
        }
        const turns = (body.turns ?? []) as ChatTurn[];
        if (turns.length > 0) {
          setMessages(
            turns.map((turn) => ({
              id: nextMessageId(),
              role: turn.role === "user" ? "user" : "assistant",
              text: turn.text,
              createdAt: turn.created_at,
              kind: "plain" as const,
            })),
          );
        }
      } catch {
        if (!cancelled) {
          setMessages((prev) => [...prev, errorMessage("could not reach the server to load history")]);
        }
      } finally {
        if (!cancelled) setHydrating(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [urlBuildId]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [messages]);

  function appendMessage(role: "user" | "assistant", text: string, kind: "plain" | "error" = "plain") {
    setMessages((prev) => [
      ...prev,
      { id: nextMessageId(), role, text, createdAt: Date.now() / 1000, kind },
    ]);
  }

  async function refreshFiles(id: string): Promise<string[]> {
    try {
      const response = await fetch(`/api/jobs/build/${encodeURIComponent(id)}/files`);
      if (!response.ok) return [];
      const body = (await response.json()) as BuildFileTreeResponse;
      return body.files ?? [];
    } catch {
      return [];
    }
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || submitting) return;

    appendMessage("user", trimmed);
    setPrompt("");
    setSubmitting(true);

    try {
      if (buildId === null) {
        await sendBuildStream(trimmed);
      } else {
        await sendEdit(buildId, trimmed);
      }
    } finally {
      setSubmitting(false);
    }
  }

  /** R-485: streams a new build via POST /api/jobs/build/stream (SSE, relaying R-484's
   * POST /jobs/build/stream) - fetch() + manual response.body.getReader() framing, not
   * EventSource, since a POST body is required. Splits the buffered text on "\n\n" event
   * boundaries and parses each frame's "data:" line as JSON. Three real shapes, verified against
   * R-484's actual live output: a {phase: "generating_ir", delta} frame (only its length is used,
   * to drive the live character-count indicator - the raw JSON text itself would render as
   * visibly broken partial JSON, not shown to the user), a {phase: "done", ...} frame (the final
   * build result, same shape the old non-streaming sendBuild() handled), and a bare
   * {credit_balance, credits_spent} frame with NO "phase" key at all (the Go relay's trailing
   * `event: credits` frame - credits arrive separately from "done" in the streaming path, unlike
   * the non-streaming response's shape, which carries both in one payload). */
  async function sendBuildStream(text: string) {
    setStreamChars(0);
    try {
      const response = await fetch("/api/jobs/build/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      });
      if (!response.ok || !response.body) {
        const body = (await response.json().catch(() => ({}))) as ErrorBody;
        appendMessage("assistant", body.error ?? `build failed with status ${response.status}`, "error");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalResult: (Partial<BuildJobResponse> & { phase?: string }) | null = null;
      let streamError: string | null = null;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const rawFrame = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          for (const line of rawFrame.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            let payload: Record<string, unknown>;
            try {
              payload = JSON.parse(line.slice("data: ".length)) as Record<string, unknown>;
            } catch {
              continue;
            }
            if (typeof payload.phase === "string") {
              if (payload.phase === "generating_ir") {
                const delta = typeof payload.delta === "string" ? payload.delta : "";
                setStreamChars((chars) => chars + delta.length);
              } else if (payload.phase === "done") {
                finalResult = payload as Partial<BuildJobResponse>;
              } else if (payload.phase === "error") {
                streamError = typeof payload.error === "string" ? payload.error : "streaming build failed";
              }
            } else if (typeof payload.credit_balance === "number") {
              setCreditBalance(payload.credit_balance);
            }
          }
          boundary = buffer.indexOf("\n\n");
        }
      }

      if (streamError) {
        appendMessage("assistant", streamError, "error");
        return;
      }
      if (!finalResult) {
        appendMessage("assistant", "the build stream ended unexpectedly", "error");
        return;
      }

      appendMessage("assistant", `Built ${finalResult.name ?? "the app"}.`);
      setWorkspace({
        buildId: finalResult.id,
        name: finalResult.name,
        description: finalResult.description,
        entities: finalResult.entities ?? [],
        fileCount: finalResult.file_count,
        commitSha: finalResult.commit_sha,
        usage: finalResult.usage,
        files: finalResult.files ?? [],
      });
      if (finalResult.id) {
        setBuildId(finalResult.id);
        hydratedFor.current = finalResult.id;
        router.replace(`/studio?build=${encodeURIComponent(finalResult.id)}`);
      }
    } catch {
      appendMessage("assistant", "could not reach the server", "error");
    } finally {
      setStreamChars(0);
    }
  }

  async function sendEdit(id: string, text: string) {
    try {
      const response = await fetch(`/api/jobs/build/${encodeURIComponent(id)}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      });
      const body = (await response.json().catch(() => ({}))) as Partial<BuildEditResponse> &
        ErrorBody;
      if (!response.ok) {
        if (response.status === 404) {
          setBuildId(null);
          hydratedFor.current = null;
          router.replace("/studio");
          appendMessage(
            "assistant",
            "This session is no longer available — start a new app.",
            "error",
          );
          return;
        }
        appendMessage("assistant", body.error ?? `edit failed with status ${response.status}`, "error");
        return;
      }
      const result = body as BuildEditResponse;
      appendMessage("assistant", result.diff?.summary || result.rationale || "Edit applied.");
      if (typeof result.credit_balance === "number") setCreditBalance(result.credit_balance);
      const files = await refreshFiles(id);
      setWorkspace((prev) => ({
        buildId: id,
        name: prev?.name,
        description: prev?.description,
        entities: result.entities ?? prev?.entities ?? [],
        fileCount: result.file_count ?? prev?.fileCount,
        commitSha: result.commit_sha ?? prev?.commitSha,
        usage: result.usage ?? prev?.usage,
        files: files.length > 0 ? files : prev?.files ?? [],
      }));
      setPreviewVersion((v) => v + 1);
    } catch {
      appendMessage("assistant", "could not reach the server", "error");
    }
  }

  return (
    <div className="studio-grid">
      <div className="studio-workspace-column">
        <StudioWorkspace snapshot={workspace} />
        <StudioTabs buildId={buildId} previewVersion={previewVersion} workspace={workspace} />
      </div>

      <div className="panel chat-rail">
        <div className="studio-credit-row">
          <span className="pill pill--accent">
            <CreditIcon width={14} height={14} />
            {creditBalance} credits
          </span>
        </div>

        <div className="chat-thread" ref={threadRef}>
          {hydrating ? <p className="chat-empty">Loading history…</p> : null}
          {!hydrating && messages.length === 0 ? (
            <p className="chat-empty">
              Describe an app in plain English — it becomes a real, owned Git repository.
            </p>
          ) : null}
          {messages.map((message) => (
            <div
              key={message.id}
              className={`chat-message chat-message--${message.role === "user" ? "user" : message.kind === "error" ? "error" : "assistant"}`}
            >
              {message.text}
            </div>
          ))}
          {submitting ? (
            <div className="chat-message chat-message--assistant">
              <span className="spinner" />{" "}
              {buildId === null
                ? streamChars > 0
                  ? `Generating your app… (${streamChars.toLocaleString()} characters so far)`
                  : "Starting…"
                : "Editing…"}
            </div>
          ) : null}
        </div>

        <form className="chat-composer" onSubmit={handleSend}>
          <textarea
            aria-label={buildId === null ? "Describe the app to build" : "Describe the change"}
            placeholder={
              buildId === null
                ? "A task tracker where users create projects and each project has tasks…"
                : "Add a favorites feature…"
            }
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            disabled={submitting}
            rows={2}
          />
          <button
            type="submit"
            className="chat-send"
            disabled={submitting || prompt.trim().length === 0}
            aria-label="Send"
          >
            <SendIcon />
          </button>
        </form>
      </div>
    </div>
  );
}
