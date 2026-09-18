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
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
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
        await sendBuild(trimmed);
      } else {
        await sendEdit(buildId, trimmed);
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function sendBuild(text: string) {
    try {
      const response = await fetch("/api/jobs/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      });
      const body = (await response.json().catch(() => ({}))) as Partial<BuildJobResponse> &
        ErrorBody;
      if (!response.ok) {
        appendMessage("assistant", body.error ?? `build failed with status ${response.status}`, "error");
        return;
      }
      const result = body as BuildJobResponse;
      appendMessage("assistant", `Built ${result.name ?? "the app"}.`);
      if (typeof result.credit_balance === "number") setCreditBalance(result.credit_balance);
      setWorkspace({
        buildId: result.id,
        name: result.name,
        description: result.description,
        entities: result.entities ?? [],
        fileCount: result.file_count,
        commitSha: result.commit_sha,
        usage: result.usage,
        files: result.files ?? [],
      });
      if (result.id) {
        setBuildId(result.id);
        hydratedFor.current = result.id;
        router.replace(`/studio?build=${encodeURIComponent(result.id)}`);
      }
    } catch {
      appendMessage("assistant", "could not reach the server", "error");
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
    } catch {
      appendMessage("assistant", "could not reach the server", "error");
    }
  }

  return (
    <div className="studio-grid">
      <StudioWorkspace snapshot={workspace} />

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
              <span className="spinner" /> {buildId === null ? "Building…" : "Editing…"}
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
