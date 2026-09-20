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
  Project,
} from "@/lib/control-plane";
import BrandMark from "@/components/brand-mark";
import { formatServerError } from "@/components/field";
import ProjectSwitcher from "@/components/project-switcher";
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

const EXAMPLE_PROMPTS = [
  "A task tracker where users create projects and each project has tasks with due dates",
  "A recipe box with tags, ratings and a weekly meal plan",
  "A simple CRM: companies, contacts and notes, with a search page",
];

const FOLLOW_UP_PROMPTS = [
  "Add user sign-in with email and password",
  "Add search and filters to the main list",
  "Add a settings page for the user profile",
];

let messageCounter = 0;
function nextMessageId(): string {
  messageCounter += 1;
  return `m${Date.now()}-${messageCounter}`;
}

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

async function fetchProjectFiles(id: string): Promise<string[]> {
  try {
    const response = await fetch(`/api/projects/${encodeURIComponent(id)}/files`);
    if (!response.ok) return [];
    const body = (await response.json()) as BuildFileTreeResponse;
    return body.files ?? [];
  } catch {
    return [];
  }
}

export default function StudioChat({
  initialCreditBalance,
  initialProjectId,
}: {
  initialCreditBalance: number;
  initialProjectId?: string;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlBuildId = searchParams.get("build");
  const urlPrompt = urlBuildId ? null : searchParams.get("prompt");

  const [projectId, setProjectId] = useState<string | null>(initialProjectId ?? null);
  const [project, setProject] = useState<Project | null>(null);
  const [buildId, setBuildId] = useState<string | null>(urlBuildId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot | null>(null);
  // Bumped after every successful edit so <StudioPreview> (rendered by <StudioTabs>) re-previews
  const [previewVersion, setPreviewVersion] = useState(0);
  const [prompt, setPrompt] = useState(urlPrompt ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [streamChars, setStreamChars] = useState(0);
  const [hydrating, setHydrating] = useState(Boolean(initialProjectId || urlBuildId));
  const [creditBalance, setCreditBalance] = useState(initialCreditBalance);

  const threadRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const hydratedFor = useRef<string | null>(null);
  const autoStarted = useRef(false);

  // Hydrate persistent project if initialProjectId is provided
  useEffect(() => {
    if (!initialProjectId || hydratedFor.current === initialProjectId) {
      return;
    }
    hydratedFor.current = initialProjectId;
    let cancelled = false;

    (async () => {
      setHydrating(true);
      try {
        // 1. Fetch project details
        const projectRes = await fetch(`/api/projects/${encodeURIComponent(initialProjectId)}`);
        if (cancelled) return;
        if (!projectRes.ok) {
          if (projectRes.status === 404) {
            setMessages([
              {
                id: nextMessageId(),
                role: "assistant",
                text: "This project is no longer available.",
                createdAt: Date.now() / 1000,
                kind: "error",
              },
            ]);
            return;
          }
          const errBody = (await projectRes.json().catch(() => ({}))) as ErrorBody;
          setMessages([
            {
              id: nextMessageId(),
              role: "assistant",
              text: formatServerError(errBody.error, "Couldn't load project details."),
              createdAt: Date.now() / 1000,
              kind: "error",
            },
          ]);
          return;
        }

        const projectData = (await projectRes.json()) as Project;
        setProject(projectData);

        // Touch opened timestamp (fire and forget)
        void fetch(`/api/projects/${encodeURIComponent(initialProjectId)}/opened`, {
          method: "POST",
        }).catch(() => {});

        // 2. Fetch turns history
        const turnsRes = await fetch(
          `/api/projects/${encodeURIComponent(initialProjectId)}/turns`,
        );
        let projectTurns: ChatTurn[] = [];
        if (turnsRes.ok) {
          const turnsBody = (await turnsRes.json()) as BuildTurnsResponse;
          projectTurns = turnsBody.turns ?? [];
        }

        if (cancelled) return;

        if (projectTurns.length > 0) {
          setMessages(
            projectTurns.map((turn) => ({
              id: nextMessageId(),
              role: turn.role === "user" ? "user" : "assistant",
              text: turn.text,
              createdAt: turn.created_at,
              kind: "plain" as const,
            })),
          );
        }

        // 3. Fetch files list
        const files = await fetchProjectFiles(initialProjectId);
        if (cancelled) return;

        setWorkspace({
          buildId: initialProjectId,
          name: projectData.name,
          description: projectData.description,
          entities: [],
          fileCount: files.length,
          files,
        });
      } catch {
        if (!cancelled) {
          setMessages([
            {
              id: nextMessageId(),
              role: "assistant",
              text: "Couldn't reach the server to load this project.",
              createdAt: Date.now() / 1000,
              kind: "error",
            },
          ]);
        }
      } finally {
        if (!cancelled) setHydrating(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [initialProjectId]);

  // Legacy hydration: fallback for ?build=<id>
  useEffect(() => {
    if (initialProjectId || !urlBuildId || hydratedFor.current === urlBuildId) {
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
      setHydrating(true);
      try {
        const response = await fetch(`/api/jobs/build/${encodeURIComponent(urlBuildId)}/turns`);
        const body = (await response.json().catch(() => ({}))) as Partial<BuildTurnsResponse> &
          ErrorBody;
        if (cancelled) return;
        if (!response.ok) {
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
  }, [initialProjectId, urlBuildId]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [messages, submitting]);

  // Home composer auto-start
  useEffect(() => {
    if (!urlPrompt || autoStarted.current) return;
    autoStarted.current = true;
    router.replace("/studio");
    formRef.current?.requestSubmit();
  }, [urlPrompt, router]);

  function appendMessage(
    role: "user" | "assistant",
    text: string,
    kind: "plain" | "error" = "plain",
  ) {
    setMessages((prev) => [
      ...prev,
      { id: nextMessageId(), role, text, createdAt: Date.now() / 1000, kind },
    ]);
  }

  function fillComposer(text: string) {
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
      if (projectId !== null) {
        await sendProjectEdit(projectId, trimmed);
      } else if (buildId !== null) {
        await sendEdit(buildId, trimmed);
      } else {
        await sendBuildStream(trimmed);
      }
    } finally {
      setSubmitting(false);
    }
  }

  function startNewApp() {
    if (submitting) return;
    setProjectId(null);
    setProject(null);
    setBuildId(null);
    hydratedFor.current = null;
    setMessages([]);
    setWorkspace(null);
    setPrompt("");
    setStreamChars(0);
    router.replace("/studio");
    textareaRef.current?.focus();
  }

  /** Streams a new build (via project if fresh) */
  async function sendBuildStream(text: string) {
    setStreamChars(0);
    try {
      // 1. Create project
      const createRes = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      });
      if (!createRes.ok) {
        const body = (await createRes.json().catch(() => ({}))) as ErrorBody;
        appendMessage(
          "assistant",
          formatServerError(body.error, `Project creation failed with status ${createRes.status}.`),
          "error",
        );
        return;
      }
      const newProject = (await createRes.json()) as Project;
      setProjectId(newProject.id);
      setProject(newProject);
      hydratedFor.current = newProject.id;
      window.history.replaceState(null, "", `/studio/${encodeURIComponent(newProject.id)}`);

      // 2. Stream build via project endpoint
      const response = await fetch(
        `/api/projects/${encodeURIComponent(newProject.id)}/build/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text }),
        },
      );
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
                streamError =
                  typeof payload.error === "string" ? payload.error : "streaming build failed";
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

      appendMessage("assistant", `Built ${finalResult.name ?? newProject.name ?? "the app"}.`);
      setProject((prev) =>
        prev ? { ...prev, name: finalResult?.name ?? prev.name, status: "active" } : null,
      );
      setWorkspace({
        buildId: newProject.id,
        name: finalResult.name ?? newProject.name,
        description: finalResult.description ?? newProject.description,
        entities: finalResult.entities ?? [],
        fileCount: finalResult.file_count,
        commitSha: finalResult.commit_sha,
        usage: finalResult.usage,
        files: finalResult.files ?? [],
      });
      setPreviewVersion((v) => v + 1);
    } catch {
      appendMessage("assistant", "Couldn't reach the server.", "error");
    } finally {
      setStreamChars(0);
    }
  }

  /** Project edit path */
  async function sendProjectEdit(id: string, text: string) {
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(id)}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      });
      const body = (await response.json().catch(() => ({}))) as Partial<BuildEditResponse> &
        ErrorBody;
      if (!response.ok) {
        if (response.status === 404) {
          appendMessage(
            "assistant",
            "This project is no longer available.",
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
      const files = await fetchProjectFiles(id);
      setWorkspace((prev) => ({
        buildId: id,
        name: prev?.name ?? project?.name,
        description: prev?.description ?? project?.description,
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

  /** Legacy edit path for builds without project */
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

  const activeProjectId = projectId ?? buildId;
  const workingLabel =
    activeProjectId === null
      ? streamChars > 0
        ? `Generating your app… ${streamChars.toLocaleString()} characters so far`
        : "Starting…"
      : "Applying your change…";
  const showEmptyThread = !hydrating && messages.length === 0 && !submitting;
  const showEmptyWorkspace = activeProjectId === null && workspace === null;
  const lastMessage = messages[messages.length - 1];
  const showFollowUps =
    !submitting &&
    activeProjectId !== null &&
    lastMessage !== undefined &&
    lastMessage.role === "assistant" &&
    lastMessage.kind === "plain";

  return (
    <div className="studio-grid">
      <aside aria-label="Chat" className="flex min-h-0 flex-col border-r border-border/60 bg-card">
        <header className="flex items-center gap-3 border-b border-border/60 px-4 py-3">
          <ProjectSwitcher
            currentProject={project}
            currentProjectId={projectId}
            currentProjectName={project?.name ?? workspace?.name}
          />
          <div className="ml-auto flex items-center gap-2">
            <Badge
              variant="secondary"
              className="gap-1 font-mono tabular-nums"
              title="Credit balance"
            >
              <Coins aria-hidden="true" />
              {creditBalance.toLocaleString("en-US")}
            </Badge>
            {activeProjectId !== null ? (
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
          </div>
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

          {showEmptyThread ? <EmptyThread onPick={fillComposer} /> : null}

          {messages.map((message) =>
            message.role === "user" ? (
              <div
                key={message.id}
                className="reveal max-w-[85%] self-end rounded-2xl rounded-br-md bg-primary px-3.5 py-2 text-[13px] leading-relaxed break-words whitespace-pre-wrap text-primary-foreground"
              >
                {message.text}
              </div>
            ) : message.kind === "error" ? (
              <div
                key={message.id}
                role="alert"
                className="reveal flex max-w-[92%] gap-2.5 self-start rounded-2xl rounded-bl-md border border-destructive/30 bg-destructive/10 px-3.5 py-2 text-[13px] leading-relaxed break-words whitespace-pre-wrap text-destructive"
              >
                <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>{message.text}</span>
              </div>
            ) : (
              <div key={message.id} className="reveal flex gap-2.5 self-stretch py-0.5">
                <BrandMark className="mt-1 size-4 shrink-0" />
                <p className="min-w-0 text-[13px] leading-relaxed break-words whitespace-pre-wrap text-foreground">
                  {message.text}
                </p>
              </div>
            ),
          )}

          {showFollowUps ? (
            <div
              className="reveal flex flex-wrap gap-1.5 pl-6.5"
              aria-label="Suggested next changes"
            >
              {FOLLOW_UP_PROMPTS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => fillComposer(suggestion)}
                  className="rounded-full border border-border/70 bg-background px-2.5 py-1 text-xs text-muted-foreground outline-none transition-colors select-none hover:border-brand/40 hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 active:translate-y-px"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          ) : null}

          {submitting ? <WorkingBubble label={workingLabel} /> : null}
        </div>

        <form ref={formRef} className="border-t border-border/60 p-3" onSubmit={handleSend}>
          {activeProjectId !== null ? (
            <p className="mb-2 px-1 text-xs text-muted-foreground">
              Editing{" "}
              <span className="font-medium text-foreground">
                {workspace?.name ?? project?.name ?? "this app"}
              </span>
              {" — "}changes apply to the same project.
            </p>
          ) : null}
          <div className="flex items-end gap-2 rounded-xl border border-input bg-background p-1.5 transition-[color,box-shadow] focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
            <textarea
              ref={textareaRef}
              aria-label={activeProjectId === null ? "Describe the app to build" : "Describe the change"}
              placeholder={
                activeProjectId === null
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
              <StudioWorkspace snapshot={workspace} buildId={buildId} projectId={projectId} />
              <StudioTabs
                buildId={buildId}
                previewVersion={previewVersion}
                workspace={workspace}
                projectId={projectId}
              />
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
      <div className="grid min-w-56 gap-2.5 rounded-2xl rounded-bl-md bg-secondary px-3.5 py-2.5 text-[13px] text-secondary-foreground">
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
