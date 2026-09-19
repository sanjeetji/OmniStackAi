"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowUp,
  Bug,
  Coins,
  FolderTree,
  LoaderCircle,
  MonitorPlay,
  Plus,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import type {
  BuildEditResponse,
  BuildFileTreeResponse,
  BuildJobResponse,
  BuildTurnsResponse,
  ChatTurn,
} from "@/lib/control-plane";
import BrandMark from "@/components/brand-mark";
import { formatServerError } from "@/components/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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

/* Real, runnable inputs - entity-style apps the builder genuinely handles - offered as one-click
 * starting points in the empty state. They fill the composer; nothing is sent until the user
 * presses Send. */
const EXAMPLE_PROMPTS = [
  "A task tracker where users create projects and each project has tasks with due dates",
  "A recipe box with tags, ratings and a weekly meal plan",
  "A simple CRM: companies, contacts and notes, with a search page",
];

let messageCounter = 0;
function nextMessageId(): string {
  messageCounter += 1;
  return `m${Date.now()}-${messageCounter}`;
}

/** The build's current file list via `GET /api/jobs/build/{id}/files` (R-474). Empty on any
 * failure - callers treat "no list" as "keep what we have", never as an error to show. Module
 * scope (no component state) so both the edit path and the `?build=` hydration effect can use it. */
async function fetchBuildFiles(id: string): Promise<string[]> {
  try {
    const response = await fetch(`/api/jobs/build/${encodeURIComponent(id)}/files`);
    if (!response.ok) return [];
    const body = (await response.json()) as BuildFileTreeResponse;
    return body.files ?? [];
  } catch {
    return [];
  }
}

export default function StudioChat({ initialCreditBalance }: { initialCreditBalance: number }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlBuildId = searchParams.get("build");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [buildId, setBuildId] = useState<string | null>(urlBuildId);
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot | null>(null);
  // Bumped after every successful edit so <StudioPreview> (rendered by <StudioTabs>) re-previews
  // this build - _edit() never restarts the preview on its own, unlike _build() (which
  // StudioPreview already re-previews for via its own buildId-change effect, so no bump is
  // needed on a fresh build).
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
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
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
          setMessages((prev) => [
            ...prev,
            errorMessage(formatServerError(body.error, "Couldn't load this build's history.")),
          ]);
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
          // R-494: turns alone left the Files/Code tabs empty after a refresh (the R-477
          // degradation). The file list is cheap and read-only, so fetch it too; the rest of the
          // snapshot (name, entities, usage) still only exists for builds made in this session.
          const files = await fetchBuildFiles(urlBuildId);
          if (!cancelled && files.length > 0) {
            setWorkspace((prev) => prev ?? { buildId: urlBuildId, entities: [], files });
          }
        }
      } catch {
        if (!cancelled) {
          setMessages((prev) => [
            ...prev,
            errorMessage("Couldn't reach the server to load this build's history."),
          ]);
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
  }, [messages, submitting]);

  function appendMessage(role: "user" | "assistant", text: string, kind: "plain" | "error" = "plain") {
    setMessages((prev) => [
      ...prev,
      { id: nextMessageId(), role, text, createdAt: Date.now() / 1000, kind },
    ]);
  }

  /** R-493: the only way to start a second app used to be editing the URL by hand. Resets this
   * session's thread and workspace and clears `?build=` - the previous build stays on the server
   * exactly as before, reachable again via its own `?build=<id>` link. */
  function startNewApp() {
    if (submitting) return;
    setBuildId(null);
    hydratedFor.current = null;
    setMessages([]);
    setWorkspace(null);
    setPrompt("");
    setStreamChars(0);
    router.replace("/studio");
    textareaRef.current?.focus();
  }

  function useExamplePrompt(text: string) {
    setPrompt(text);
    textareaRef.current?.focus();
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
        appendMessage(
          "assistant",
          formatServerError(body.error, `Build failed with status ${response.status}.`),
          "error",
        );
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
        appendMessage("assistant", formatServerError(streamError, "The build failed."), "error");
        return;
      }
      if (!finalResult) {
        appendMessage("assistant", "The build stream ended unexpectedly.", "error");
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
      appendMessage("assistant", "Couldn't reach the server.", "error");
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
        appendMessage(
          "assistant",
          formatServerError(body.error, `Edit failed with status ${response.status}.`),
          "error",
        );
        return;
      }
      const result = body as BuildEditResponse;
      appendMessage("assistant", result.diff?.summary || result.rationale || "Edit applied.");
      if (typeof result.credit_balance === "number") setCreditBalance(result.credit_balance);
      const files = await fetchBuildFiles(id);
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
      appendMessage("assistant", "Couldn't reach the server.", "error");
    }
  }

  const workingLabel =
    buildId === null
      ? streamChars > 0
        ? `Generating your app… ${streamChars.toLocaleString()} characters so far`
        : "Starting…"
      : "Applying your change…";
  const showEmptyThread = !hydrating && messages.length === 0 && !submitting;
  const showEmptyWorkspace = buildId === null && workspace === null;

  return (
    <div className="studio-grid">
      <aside aria-label="Chat" className="flex min-h-0 flex-col border-r border-border/60 bg-card">
        <header className="flex items-center gap-3 border-b border-border/60 px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">
              {workspace?.name ?? (buildId ? "Your app" : "New app")}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {buildId ? "Chat to keep changing it" : "Describe it to start building"}
            </p>
          </div>
          <Badge
            variant="secondary"
            className="gap-1 font-mono tabular-nums"
            title="Credit balance"
          >
            <Coins aria-hidden="true" />
            {creditBalance.toLocaleString("en-US")}
          </Badge>
          {buildId !== null ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={startNewApp}
              disabled={submitting}
            >
              <Plus aria-hidden="true" />
              New app
            </Button>
          ) : null}
        </header>

        <div
          ref={threadRef}
          role="log"
          aria-label="Conversation"
          aria-busy={hydrating}
          className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4"
        >
          {hydrating ? (
            <>
              <Skeleton className="h-10 w-3/5 self-end rounded-2xl rounded-br-md" />
              <Skeleton className="h-16 w-4/5 self-start rounded-2xl rounded-bl-md" />
            </>
          ) : null}

          {showEmptyThread ? <EmptyThread onPick={useExamplePrompt} /> : null}

          {messages.map((message) =>
            message.role === "user" ? (
              <div
                key={message.id}
                className="reveal max-w-[85%] self-end rounded-2xl rounded-br-md bg-primary px-3.5 py-2.5 text-sm break-words whitespace-pre-wrap text-primary-foreground"
              >
                {message.text}
              </div>
            ) : message.kind === "error" ? (
              <div
                key={message.id}
                role="alert"
                className="reveal flex max-w-[92%] gap-2.5 self-start rounded-2xl rounded-bl-md border border-destructive/30 bg-destructive/10 px-3.5 py-2.5 text-sm break-words whitespace-pre-wrap text-destructive"
              >
                <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>{message.text}</span>
              </div>
            ) : (
              <div key={message.id} className="reveal flex max-w-[92%] gap-2.5 self-start">
                <BrandMark className="mt-1.5 size-5 shrink-0" />
                <div className="rounded-2xl rounded-bl-md bg-secondary px-3.5 py-2.5 text-sm break-words whitespace-pre-wrap text-secondary-foreground">
                  {message.text}
                </div>
              </div>
            ),
          )}

          {submitting ? <WorkingBubble label={workingLabel} /> : null}
        </div>

        <form className="border-t border-border/60 p-3" onSubmit={handleSend}>
          {buildId !== null ? (
            <p className="mb-2 px-1 text-xs text-muted-foreground">
              Editing{" "}
              <span className="font-medium text-foreground">{workspace?.name ?? "this app"}</span>
              {" — "}changes apply to the same repository.
            </p>
          ) : null}
          <div className="flex items-end gap-2 rounded-xl border border-input bg-background p-1.5 transition-[color,box-shadow] focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
            <textarea
              ref={textareaRef}
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
              rows={1}
              className="field-sizing-content max-h-40 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-60"
            />
            <Button
              type="submit"
              size="icon"
              aria-label="Send"
              disabled={submitting || prompt.trim().length === 0}
            >
              {submitting ? (
                <LoaderCircle className="animate-spin" aria-hidden="true" />
              ) : (
                <ArrowUp aria-hidden="true" />
              )}
            </Button>
          </div>
          <p className="mt-1.5 px-1 text-[11px] text-muted-foreground">
            Enter to send · Shift+Enter for a new line
          </p>
        </form>
      </aside>

      <section aria-label="Workspace" className="relative flex min-h-0 flex-col overflow-y-auto">
        {submitting ? (
          <div className="studio-progress" role="progressbar" aria-label="Working" />
        ) : null}
        <div className="flex flex-1 flex-col gap-5 p-6">
          {showEmptyWorkspace ? (
            <EmptyWorkspace />
          ) : (
            <>
              <StudioWorkspace snapshot={workspace} buildId={buildId} />
              <StudioTabs buildId={buildId} previewVersion={previewVersion} workspace={workspace} />
            </>
          )}
        </div>
      </section>
    </div>
  );
}

function EmptyThread({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="reveal my-auto grid gap-4 px-1 py-6 text-center">
      <BrandMark className="mx-auto size-9" />
      <div>
        <h2 className="text-base font-semibold">What do you want to build?</h2>
        <p className="mt-1 text-pretty text-sm text-muted-foreground">
          Describe it in plain language. You get a real codebase, a live preview, and this chat to
          keep changing it.
        </p>
      </div>
      <ul className="grid gap-2 text-left" aria-label="Example prompts">
        {EXAMPLE_PROMPTS.map((example) => (
          <li key={example}>
            <button
              type="button"
              onClick={() => onPick(example)}
              className="flex w-full items-start gap-2 rounded-xl border border-border/70 bg-background px-3 py-2.5 text-left text-sm text-muted-foreground outline-none transition-colors hover:border-brand/40 hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 active:translate-y-px"
            >
              <Sparkles className="mt-0.5 size-3.5 shrink-0 text-brand" aria-hidden="true" />
              <span>{example}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function WorkingBubble({ label }: { label: string }) {
  return (
    <div className="flex max-w-[92%] gap-2.5 self-start" aria-live="polite">
      <BrandMark className="mt-1.5 size-5 shrink-0" />
      <div className="grid min-w-56 gap-2.5 rounded-2xl rounded-bl-md bg-secondary px-3.5 py-2.5 text-sm text-secondary-foreground">
        <p className="flex items-center gap-2">
          <LoaderCircle className="size-4 shrink-0 animate-spin text-brand" aria-hidden="true" />
          <span>{label}</span>
        </p>
        <div className="grid gap-1.5" aria-hidden="true">
          <Skeleton className="h-2.5 w-40" />
          <Skeleton className="h-2.5 w-52" />
          <Skeleton className="h-2.5 w-32" />
        </div>
      </div>
    </div>
  );
}

const WORKSPACE_CAPABILITIES = [
  {
    icon: MonitorPlay,
    title: "Live preview",
    body: "The running app, refreshed after every change.",
  },
  {
    icon: FolderTree,
    title: "Files and code",
    body: "Every generated file, with syntax highlighting.",
  },
  {
    icon: Bug,
    title: "Problems",
    body: "A real TypeScript check, on demand.",
  },
];

function EmptyWorkspace() {
  return (
    <div className="reveal m-auto grid w-full max-w-lg gap-6 py-10 text-center">
      <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-secondary text-muted-foreground">
        <Sparkles className="size-6" aria-hidden="true" />
      </div>
      <div>
        <h2 className="text-balance text-xl font-semibold tracking-tight">
          Your app will show up here
        </h2>
        <p className="mt-2 text-pretty text-sm text-muted-foreground">
          Once the first build finishes, this panel becomes the workspace.
        </p>
      </div>
      <ul className="grid gap-2 text-left sm:grid-cols-3">
        {WORKSPACE_CAPABILITIES.map(({ icon: Icon, title, body }) => (
          <li key={title} className="rounded-xl border border-border/70 bg-card p-3">
            <Icon className="size-4 text-brand" aria-hidden="true" />
            <p className="mt-2 text-sm font-medium">{title}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{body}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
