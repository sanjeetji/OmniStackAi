"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowUp,
  BookOpen,
  Bug,
  Coins,
  FileText,
  FolderTree,
  LoaderCircle,
  Mic,
  MicOff,
  MonitorPlay,
  Paperclip,
  Plus,
  Sparkles,
  Square,
  TriangleAlert,
  X,
  LayoutTemplate,
} from "lucide-react";
import type {
  BuildEditResponse,
  BuildFileTreeResponse,
  BuildJobResponse,
  BuildTurnsResponse,
  ChatTurn,
  Project,
  ProjectKnowledge,
  Skill,
} from "@/lib/control-plane";
import BrandMark from "@/components/brand-mark";
import { formatServerError } from "@/components/field";
import ProjectSwitcher from "@/components/project-switcher";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { StudioTabs } from "./studio-tabs";
import { StudioWorkspace, type WorkspaceSnapshot } from "./studio-workspace";

interface BuildStreamResult extends Partial<BuildJobResponse> {
  phase?: string;
  context_truncated?: boolean;
  active_skills?: string[];
  truncated_skills?: string[];
}

interface AttachmentItem {
  id: string;
  name: string;
  size: number;
  content: string;
}

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
  startedFromTemplate,
}: {
  initialCreditBalance: number;
  initialProjectId?: string;
  /** Set when the project was created from a marketplace template (R-523). Its chat edits are made
   * by the code-edit agent, which changes the real files, checks them and commits (R-525). */
  startedFromTemplate?: { name: string; version: string };
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

  // Skills & Knowledge state
  const [projectKnowledge, setProjectKnowledge] = useState<ProjectKnowledge | null>(null);
  const [attachedSkills, setAttachedSkills] = useState<Skill[]>([]);
  const [allUserSkills, setAllUserSkills] = useState<Skill[]>([]);
  const [excludedSkills, setExcludedSkills] = useState<Set<string>>(new Set());
  const [excludeKnowledge, setExcludeKnowledge] = useState(false);
  const [mentionSkills, setMentionSkills] = useState<Set<string>>(new Set());
  const [truncationWarning, setTruncationWarning] = useState<{
    truncated: boolean;
    activeSkills: string[];
    truncatedSkills: string[];
  } | null>(null);

  // Mention autocomplete state
  const [mentionPickerOpen, setMentionPickerOpen] = useState(false);
  const [mentionQuery, setMentionQuery] = useState("");
  const [mentionStartIndex, setMentionStartIndex] = useState(0);
  const [selectedMentionIndex, setSelectedMentionIndex] = useState(0);

  // Cancellation, Voice Input, and Attachments (R-506)
  const [speechSupported, setSpeechSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [attachments, setAttachments] = useState<AttachmentItem[]>([]);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);

  const threadRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const hydratedFor = useRef<string | null>(null);
  const autoStarted = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const activeBuildingProjectId = useRef<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Fetch user skills library once for mention autocomplete
  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch("/api/skills");
        if (res.ok) {
          const data = await res.json();
          setAllUserSkills(data.skills ?? []);
        }
      } catch {
        // non-blocking
      }
    })();
  }, []);

  // Web Speech API initialization
  useEffect(() => {
    const win = typeof window !== "undefined" ? (window as any) : {};
    const SpeechRec = win.SpeechRecognition || win.webkitSpeechRecognition;
    if (SpeechRec) {
      void Promise.resolve().then(() => {
        setSpeechSupported(true);
      });
    }
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  const toggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      return;
    }
    const win = typeof window !== "undefined" ? (window as any) : {};
    const SpeechRec = win.SpeechRecognition || win.webkitSpeechRecognition;
    if (!SpeechRec) return;

    try {
      const rec = new SpeechRec();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";

      rec.onstart = () => {
        setIsListening(true);
      };

      rec.onresult = (event: any) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript.trim()) {
          setPrompt((prev) => (prev ? `${prev} ${transcript.trim()}` : transcript.trim()));
        }
      };

      rec.onerror = (event: any) => {
        console.warn("Speech recognition error:", event.error);
        setIsListening(false);
      };

      rec.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = rec;
      rec.start();
    } catch (err) {
      console.warn("Speech recognition start failed:", err);
      setIsListening(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setAttachmentError(null);

    const allowedExtensions = [
      ".md", ".txt", ".json", ".csv", ".sql", ".ts", ".tsx", ".py"
    ];
    const imageExtensions = [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"];

    if (attachments.length + files.length > 4) {
      setAttachmentError("Maximum 4 attachments per message.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    const newAttachments: AttachmentItem[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const name = file.name.toLowerCase();
      const ext = name.substring(name.lastIndexOf("."));

      if (imageExtensions.includes(ext)) {
        setAttachmentError("Images are not supported on the active model. Attach text files (.md, .txt, .json, .csv, .sql, .ts, .tsx, .py).");
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }

      if (!allowedExtensions.includes(ext)) {
        setAttachmentError(`Unsupported file type: ${file.name}. Allowed: ${allowedExtensions.join(", ")}`);
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }

      if (file.size > 256 * 1024) {
        setAttachmentError(`File ${file.name} exceeds 256 KB limit.`);
        if (fileInputRef.current) fileInputRef.current.value = "";
        return;
      }

      try {
        const text = await file.text();
        newAttachments.push({
          id: `att-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          name: file.name,
          size: file.size,
          content: text,
        });
      } catch {
        setAttachmentError(`Failed to read file ${file.name}.`);
      }
    }

    setAttachments((prev) => [...prev, ...newAttachments]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  const handleCancel = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    const currentId = activeBuildingProjectId.current || projectId;
    if (currentId) {
      try {
        await fetch(`/api/projects/${encodeURIComponent(currentId)}/build/cancel`, {
          method: "POST",
        });
      } catch {
        // non-blocking
      }
    }
    appendMessage("assistant", "Stopped. Nothing was committed.");
    setSubmitting(false);
    setStreamChars(0);
  };

  // Fetch project knowledge and attached skills
  useEffect(() => {
    let active = true;
    if (!projectId) {
      void Promise.resolve().then(() => {
        if (active) {
          setProjectKnowledge(null);
          setAttachedSkills([]);
        }
      });
      return () => {
        active = false;
      };
    }
    void (async () => {
      try {
        const [knowRes, skillsRes] = await Promise.all([
          fetch(`/api/projects/${encodeURIComponent(projectId)}/knowledge`),
          fetch(`/api/projects/${encodeURIComponent(projectId)}/skills`),
        ]);
        if (!active) return;
        if (knowRes.ok) {
          const k: ProjectKnowledge = await knowRes.json();
          setProjectKnowledge(k);
        }
        if (skillsRes.ok) {
          const s = await skillsRes.json();
          setAttachedSkills(s.skills ?? []);
        }
      } catch {
        // non-blocking
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

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
    if ((!trimmed && attachments.length === 0) || submitting) return;

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    }

    let userVisibleText = trimmed;
    let fullPrompt = trimmed;
    if (attachments.length > 0) {
      const attSummary = attachments.map((a) => `📎 ${a.name}`).join(", ");
      userVisibleText = trimmed ? `${trimmed}\n\n${attSummary}` : attSummary;
      const blocks = attachments.map((att) => {
        const ext = att.name.split(".").pop() || "";
        return `\n\n--- Attachment: ${att.name} ---\n\`\`\`${ext}\n${att.content}\n\`\`\``;
      });
      fullPrompt = `${trimmed || "Please review the attached files."}${blocks.join("")}`;
    }

    appendMessage("user", userVisibleText);
    setPrompt("");
    setAttachments([]);
    setSubmitting(true);

    try {
      if (projectId !== null) {
        await sendProjectEdit(projectId, fullPrompt);
      } else if (buildId !== null) {
        await sendEdit(buildId, fullPrompt);
      } else {
        await sendBuildStream(fullPrompt);
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

  const computeMentionSkills = (text: string): string[] => {
    const textMentions = Array.from(text.matchAll(/@([a-z0-9]+(?:-[a-z0-9]+)*)/g)).map(
      (m) => m[1],
    );
    const set = new Set<string>();
    for (const s of attachedSkills) {
      if (!excludedSkills.has(s.name)) {
        set.add(s.name);
      }
    }
    for (const m of mentionSkills) {
      if (!excludedSkills.has(m)) {
        set.add(m);
      }
    }
    for (const m of textMentions) {
      if (!excludedSkills.has(m)) {
        set.add(m);
      }
    }
    return Array.from(set);
  };

  const filteredSkills = allUserSkills.filter((s) =>
    s.name.toLowerCase().includes(mentionQuery),
  );

  const handlePromptChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = event.target.value;
    const sel = event.target.selectionStart;
    setPrompt(val);

    const textBefore = val.slice(0, sel);
    const match = textBefore.match(/(?:^|\s)@([a-z0-9-]*)$/i);
    if (match) {
      setMentionQuery(match[1].toLowerCase());
      setMentionStartIndex(sel - match[1].length - 1);
      setMentionPickerOpen(true);
      setSelectedMentionIndex(0);
    } else {
      setMentionPickerOpen(false);
    }
  };

  const insertMention = (skillName: string) => {
    const before = prompt.slice(0, mentionStartIndex);
    const after = prompt.slice(mentionStartIndex + mentionQuery.length + 1);
    const newText = `${before}@${skillName} ${after}`;
    setPrompt(newText);
    setMentionPickerOpen(false);
    setMentionSkills((prev) => new Set(prev).add(skillName));
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const cursor = before.length + skillName.length + 2;
        textareaRef.current.setSelectionRange(cursor, cursor);
      }
    }, 0);
  };

  const handlePromptKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (mentionPickerOpen && filteredSkills.length > 0) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelectedMentionIndex((i) => (i + 1) % filteredSkills.length);
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelectedMentionIndex((i) => (i - 1 + filteredSkills.length) % filteredSkills.length);
        return;
      }
      if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        if (filteredSkills[selectedMentionIndex]) {
          insertMention(filteredSkills[selectedMentionIndex].name);
        }
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        setMentionPickerOpen(false);
        return;
      }
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  /** Streams a new build (via project if fresh) */
  async function sendBuildStream(text: string) {
    setStreamChars(0);
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      // 1. Create project
      const createRes = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
        signal: controller.signal,
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
      activeBuildingProjectId.current = newProject.id;
      setProjectId(newProject.id);
      setProject(newProject);
      hydratedFor.current = newProject.id;
      window.history.replaceState(null, "", `/studio/${encodeURIComponent(newProject.id)}`);

      // 2. Stream build via project endpoint
      const mentionList = computeMentionSkills(text);
      const response = await fetch(
        `/api/projects/${encodeURIComponent(newProject.id)}/build/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text, mention_skills: mentionList }),
          signal: controller.signal,
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
      let finalResult: BuildStreamResult | null = null;
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
              } else if (payload.phase === "cancelled") {
                appendMessage("assistant", "Stopped. Nothing was committed.");
                return;
              } else if (payload.phase === "done") {
                finalResult = payload as unknown as BuildStreamResult;
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

      if (finalResult.context_truncated) {
        setTruncationWarning({
          truncated: true,
          activeSkills: Array.isArray(finalResult.active_skills) ? finalResult.active_skills : [],
          truncatedSkills: Array.isArray(finalResult.truncated_skills)
            ? finalResult.truncated_skills
            : [],
        });
      } else {
        setTruncationWarning(null);
      }
      setExcludedSkills(new Set());
      setExcludeKnowledge(false);
      setMentionSkills(new Set());

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
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      appendMessage("assistant", "Couldn't reach the server.", "error");
    } finally {
      abortControllerRef.current = null;
      activeBuildingProjectId.current = null;
      setStreamChars(0);
    }
  }

  /** Project edit path */
  async function sendProjectEdit(id: string, text: string) {
    const controller = new AbortController();
    abortControllerRef.current = controller;
    activeBuildingProjectId.current = id;

    try {
      const mentionList = computeMentionSkills(text);
      const response = await fetch(`/api/projects/${encodeURIComponent(id)}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text, mention_skills: mentionList }),
        signal: controller.signal,
      });
      const body = (await response.json().catch(() => ({}))) as Partial<BuildEditResponse> &
        ErrorBody & {
          context_truncated?: boolean;
          active_skills?: string[];
          truncated_skills?: string[];
        };
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
      const result = body as BuildEditResponse & {
        context_truncated?: boolean;
        active_skills?: string[];
        truncated_skills?: string[];
      };
      if (result.context_truncated) {
        setTruncationWarning({
          truncated: true,
          activeSkills: Array.isArray(result.active_skills) ? result.active_skills : [],
          truncatedSkills: Array.isArray(result.truncated_skills) ? result.truncated_skills : [],
        });
      } else {
        setTruncationWarning(null);
      }
      setExcludedSkills(new Set());
      setExcludeKnowledge(false);
      setMentionSkills(new Set());

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
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      appendMessage("assistant", "Couldn't reach the server.", "error");
    } finally {
      abortControllerRef.current = null;
      activeBuildingProjectId.current = null;
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

        {truncationWarning?.truncated && (
          <div
            role="alert"
            className="mx-3 mb-2 flex items-start justify-between gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-2.5 text-xs text-amber-800 dark:text-amber-200"
          >
            <div className="flex items-start gap-2">
              <AlertCircle className="size-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
              <div>
                <p className="font-semibold">Context truncated to fit prompt limit</p>
                <p className="text-[11px] opacity-90 mt-0.5">
                  Project knowledge was prioritized; some skills were omitted.
                  {truncationWarning.truncatedSkills.length > 0 && (
                    <span>
                      {" "}Omitted:{" "}
                      <span className="font-mono">
                        {truncationWarning.truncatedSkills.map((s) => `@${s}`).join(", ")}
                      </span>.
                    </span>
                  )}
                  {truncationWarning.activeSkills.length > 0 && (
                    <span>
                      {" "}Active:{" "}
                      <span className="font-mono">
                        {truncationWarning.activeSkills.map((s) => `@${s}`).join(", ")}
                      </span>.
                    </span>
                  )}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setTruncationWarning(null)}
              className="text-amber-700 dark:text-amber-300 hover:text-amber-950 dark:hover:text-amber-100"
              title="Dismiss"
            >
              <X className="size-3.5" />
            </button>
          </div>
        )}

        <form ref={formRef} className="border-t border-border/60 p-3" onSubmit={handleSend}>
          {startedFromTemplate ? (
            <div className="mb-2 flex items-start gap-2 rounded-lg border border-border/60 bg-muted/50 px-3 py-2 text-xs">
              <LayoutTemplate className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
              <p className="text-pretty text-muted-foreground">
                Started from the{" "}
                <span className="font-medium text-foreground">{startedFromTemplate.name}</span>{" "}
                template (v{startedFromTemplate.version}). It&rsquo;s your own copy: ask for any change
                and it&rsquo;s made in the code, checked, and saved as a new version.
              </p>
            </div>
          ) : activeProjectId !== null ? (
            <p className="mb-2 px-1 text-xs text-muted-foreground">
              Editing{" "}
              <span className="font-medium text-foreground">
                {workspace?.name ?? project?.name ?? "this app"}
              </span>
              {" — "}changes apply to the same project.
            </p>
          ) : null}

          {/* Active Context Chips Row */}
          {(projectKnowledge?.knowledge || attachedSkills.length > 0 || mentionSkills.size > 0) && (
            <div className="mb-2 flex flex-wrap items-center gap-1.5 px-1 text-xs">
              <span className="text-[11px] font-medium text-muted-foreground mr-0.5">Context:</span>
              {projectKnowledge?.knowledge && (
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs transition-colors",
                    excludeKnowledge
                      ? "border border-dashed border-border/60 text-muted-foreground/50 line-through cursor-pointer"
                      : "bg-brand/10 border border-brand/30 text-brand font-medium",
                  )}
                  title={
                    excludeKnowledge
                      ? "Click to include project knowledge"
                      : "Project knowledge applied to every message. Click x to exclude for next message."
                  }
                  onClick={excludeKnowledge ? () => setExcludeKnowledge(false) : undefined}
                >
                  <BookOpen className="size-3 shrink-0" />
                  Knowledge
                  {!excludeKnowledge && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setExcludeKnowledge(true);
                      }}
                      className="hover:text-foreground text-brand/80 ml-0.5"
                      title="Exclude for next message"
                    >
                      <X className="size-3" />
                    </button>
                  )}
                </span>
              )}

              {attachedSkills.map((s) => {
                const isExcluded = excludedSkills.has(s.name);
                return (
                  <span
                    key={s.id}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs transition-colors",
                      isExcluded
                        ? "border border-dashed border-border/60 text-muted-foreground/50 line-through cursor-pointer"
                        : "bg-secondary text-secondary-foreground font-mono",
                    )}
                    title={
                      isExcluded
                        ? `Click to include @${s.name}`
                        : `${s.title}: ${s.description || s.body.slice(0, 100)}. Click x to exclude for next message.`
                    }
                    onClick={
                      isExcluded
                        ? () =>
                            setExcludedSkills((prev) => {
                              const next = new Set(prev);
                              next.delete(s.name);
                              return next;
                            })
                        : undefined
                    }
                  >
                    <span>@{s.name}</span>
                    {!isExcluded && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setExcludedSkills((prev) => new Set(prev).add(s.name));
                        }}
                        className="hover:text-destructive text-muted-foreground ml-0.5"
                        title="Exclude for next message"
                      >
                        <X className="size-3" />
                      </button>
                    )}
                  </span>
                );
              })}

              {Array.from(mentionSkills)
                .filter((m) => !attachedSkills.some((s) => s.name === m))
                .map((name) => {
                  const isExcluded = excludedSkills.has(name);
                  return (
                    <span
                      key={name}
                      className={cn(
                        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs transition-colors",
                        isExcluded
                          ? "border border-dashed border-border/60 text-muted-foreground/50 line-through cursor-pointer"
                          : "bg-brand/10 border border-brand/30 text-brand font-mono",
                      )}
                      title={`Mentioned skill @${name}`}
                      onClick={
                        isExcluded
                          ? () =>
                              setExcludedSkills((prev) => {
                                const next = new Set(prev);
                                next.delete(name);
                                return next;
                              })
                          : undefined
                      }
                    >
                      <span>@{name}</span>
                      {!isExcluded && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setMentionSkills((prev) => {
                              const next = new Set(prev);
                              next.delete(name);
                              return next;
                            });
                          }}
                          className="hover:text-destructive text-muted-foreground ml-0.5"
                          title="Remove mention"
                        >
                          <X className="size-3" />
                        </button>
                      )}
                    </span>
                  );
                })}
            </div>
          )}

          {/* Autocomplete picker for @mentions */}
          {mentionPickerOpen && filteredSkills.length > 0 && (
            <div className="mb-2 max-h-48 overflow-y-auto rounded-lg border border-border bg-popover p-1 shadow-lg text-popover-foreground text-xs">
              <div className="px-2 py-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Skills Library (@mention)
              </div>
              {filteredSkills.map((skill, idx) => (
                <button
                  key={skill.id}
                  type="button"
                  onClick={() => insertMention(skill.name)}
                  className={cn(
                    "w-full flex items-center justify-between rounded-md px-2 py-1.5 text-left transition-colors",
                    idx === selectedMentionIndex
                      ? "bg-accent text-accent-foreground font-medium"
                      : "hover:bg-muted/50",
                  )}
                >
                  <span className="font-mono font-medium text-brand">@{skill.name}</span>
                  <span className="text-muted-foreground text-[11px] truncate max-w-[200px]">
                    {skill.title}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Attachment chips */}
          {attachments.length > 0 && (
            <div className="mb-2 flex flex-wrap items-center gap-1.5 px-1">
              {attachments.map((att) => (
                <span
                  key={att.id}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border/70 bg-muted/60 px-2.5 py-1 text-xs text-foreground"
                >
                  <FileText className="size-3.5 text-muted-foreground shrink-0" />
                  <span className="font-medium truncate max-w-[150px]">{att.name}</span>
                  <span className="text-[10px] text-muted-foreground font-mono">
                    ({Math.round(att.size / 1024) || 1} KB)
                  </span>
                  <button
                    type="button"
                    onClick={() => removeAttachment(att.id)}
                    className="text-muted-foreground hover:text-destructive ml-0.5"
                    title="Remove attachment"
                  >
                    <X className="size-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Attachment error */}
          {attachmentError && (
            <div className="mb-2 flex items-center justify-between rounded-lg border border-destructive/30 bg-destructive/10 px-2.5 py-1.5 text-xs text-destructive">
              <span>{attachmentError}</span>
              <button type="button" onClick={() => setAttachmentError(null)}>
                <X className="size-3" />
              </button>
            </div>
          )}

          <div className="flex items-end gap-2 rounded-xl border border-input bg-background p-1.5 transition-[color,box-shadow] focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
            {/* Hidden file input for attachments */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              multiple
              accept=".md,.txt,.json,.csv,.sql,.ts,.tsx,.py,text/plain,application/json,text/markdown,text/csv"
              className="hidden"
            />

            <textarea
              ref={textareaRef}
              aria-label={
                activeProjectId === null ? "Describe the app to build" : "Describe the change"
              }
              placeholder={
                activeProjectId === null
                  ? "A task tracker where users create projects and each project has tasks… (type @ for skills)"
                  : "Add a favorites feature… (type @ for skills)"
              }
              value={prompt}
              onChange={handlePromptChange}
              onKeyDown={handlePromptKeyDown}
              disabled={submitting}
              rows={1}
              className="field-sizing-content max-h-40 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none placeholder:text-muted-foreground disabled:opacity-60"
            />

            {/* Paperclip attachment button */}
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={() => fileInputRef.current?.click()}
              disabled={submitting || attachments.length >= 4}
              className="size-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60"
              title="Attach files (.md, .txt, .json, .csv, .sql, .ts, .tsx, .py)"
              aria-label="Attach files"
            >
              <Paperclip className="size-4" aria-hidden="true" />
            </Button>

            {/* Mic speech recognition button */}
            {speechSupported && (
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={toggleListening}
                disabled={submitting}
                className={cn(
                  "size-8 rounded-lg transition-colors",
                  isListening
                    ? "bg-red-500/15 text-red-600 hover:bg-red-500/25 dark:text-red-400 animate-pulse"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/60",
                )}
                title={isListening ? "Stop listening" : "Voice input"}
                aria-label={isListening ? "Stop listening" : "Voice input"}
              >
                {isListening ? (
                  <MicOff className="size-4 text-red-600 dark:text-red-400" aria-hidden="true" />
                ) : (
                  <Mic className="size-4" aria-hidden="true" />
                )}
              </Button>
            )}

            {/* Send or Stop button */}
            {submitting ? (
              <Button
                type="button"
                size="icon"
                variant="destructive"
                aria-label="Stop generation"
                onClick={handleCancel}
                title="Stop generation"
                className="size-8 rounded-lg"
              >
                <Square className="size-3.5 fill-current" aria-hidden="true" />
              </Button>
            ) : (
              <Button
                type="submit"
                size="icon"
                aria-label="Send"
                disabled={prompt.trim().length === 0 && attachments.length === 0}
                className="size-8 rounded-lg"
              >
                <ArrowUp aria-hidden="true" />
              </Button>
            )}
          </div>
          <p className="mt-1.5 px-1 text-[11px] text-muted-foreground">
            Enter to send · Shift+Enter for a new line · Type @ to mention skills
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
