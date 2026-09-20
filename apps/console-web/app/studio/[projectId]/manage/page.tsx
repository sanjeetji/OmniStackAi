"use client";

import { use, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Archive,
  ArrowLeft,
  BookOpen,
  Check,
  CheckCircle2,
  Coins,
  Copy,
  Cpu,
  Database,
  Download,
  ExternalLink,
  Eye,
  EyeOff,
  FileCode2,
  GitBranch,
  Globe,
  Key,
  LoaderCircle,
  Lock,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldAlert,
  Sparkles,
  Terminal,
  Trash2,
  Unlink,
  Plug,
  X,
} from "lucide-react";

function GithubIcon({ className = "size-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}
import type {
  GitConnectionStatus,
  Project,
  ProjectGitStatus,
  ProjectKnowledge,
  SecretMetadata,
  Skill,
} from "@/lib/control-plane";
import { formatDateTime, formatRelativeTime } from "@/lib/time";
import { DeleteDialog } from "@/components/project-dialogs";
import { ProjectAIManage } from "@/components/project-ai-manage";
import { ProjectDbManage } from "@/components/project-db-manage";
import { ProjectLogsManage } from "@/components/project-logs-manage";
import { ProjectSEOManage } from "@/components/project-seo-manage";
import { ProjectSecurityManage } from "@/components/project-security-manage";
import { ProjectTestsManage } from "@/components/project-tests-manage";
import { ProjectPublishManage } from "@/components/project-publish-manage";
import { ProjectDomainManage } from "@/components/project-domain-manage";
import { ProjectConnectorsManage } from "@/components/project-connectors-manage";
import { SkillEditorDialog } from "@/components/skills-library";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export default function ProjectManagePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const router = useRouter();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Section nav: "general" | "knowledge" | "skills" | "secrets" | "git" | "ai" | "seo" | "logs" | "database" | "security" | "tests" | "publish" | "domains" | "connectors"
  const [activeSection, setActiveSection] = useState<
    "general" | "knowledge" | "skills" | "secrets" | "git" | "ai" | "seo" | "logs" | "database" | "security" | "tests" | "publish" | "domains" | "connectors"
  >("general");

  // General Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Knowledge state (16 KB max)
  const [knowledge, setKnowledge] = useState("");
  const [knowledgeUpdatedAt, setKnowledgeUpdatedAt] = useState<string | null>(null);
  const [loadingKnowledge, setLoadingKnowledge] = useState(false);
  const [savingKnowledge, setSavingKnowledge] = useState(false);
  const [savedKnowledgeSuccess, setSavedKnowledgeSuccess] = useState(false);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);

  // Skills state
  const [projectSkills, setProjectSkills] = useState<Skill[]>([]);
  const [allUserSkills, setAllUserSkills] = useState<Skill[]>([]);
  const [loadingSkills, setLoadingSkills] = useState(false);
  const [skillsError, setSkillsError] = useState<string | null>(null);
  const [attachingSkillId, setAttachingSkillId] = useState<string | null>(null);
  const [detachingSkillId, setDetachingSkillId] = useState<string | null>(null);
  const [addSkillDialogOpen, setAddSkillDialogOpen] = useState(false);
  const [newSkillDialogOpen, setNewSkillDialogOpen] = useState(false);

  // Git state
  const [gitStatus, setGitStatus] = useState<GitConnectionStatus | null>(null);
  const [projectGit, setProjectGit] = useState<ProjectGitStatus | null>(null);
  const [loadingGit, setLoadingGit] = useState(false);
  const [gitError, setGitError] = useState<string | null>(null);
  const [unconfiguredNotice, setUnconfiguredNotice] = useState<string | null>(null);
  const [connectingGit, setConnectingGit] = useState(false);
  const [disconnectingGit, setDisconnectingGit] = useState(false);
  const [creatingRepo, setCreatingRepo] = useState(false);
  const [pushingGit, setPushingGit] = useState(false);
  const [pushSuccess, setPushSuccess] = useState(false);
  const [copiedClone, setCopiedClone] = useState(false);
  const [repoName, setRepoName] = useState("");
  const [repoPrivate, setRepoPrivate] = useState(true);

  // Secrets state (F-05)
  const [secrets, setSecrets] = useState<SecretMetadata[]>([]);
  const [loadingSecrets, setLoadingSecrets] = useState(false);
  const [secretsError, setSecretsError] = useState<string | null>(null);
  const [revealedSecrets, setRevealedSecrets] = useState<Record<string, { value: string; expiresAt: number }>>({});
  const [revealingKey, setRevealingKey] = useState<string | null>(null);
  const [addSecretOpen, setAddSecretOpen] = useState(false);
  const [editingSecret, setEditingSecret] = useState(false);
  const [secretKey, setSecretKey] = useState("");
  const [secretValue, setSecretValue] = useState("");
  const [secretDescription, setSecretDescription] = useState("");
  const [secretKeyError, setSecretKeyError] = useState<string | null>(null);
  const [savingSecret, setSavingSecret] = useState(false);
  const [deleteSecretKey, setDeleteSecretKey] = useState<string | null>(null);
  const [deletingSecret, setDeletingSecret] = useState(false);
  const [secretsUpdated, setSecretsUpdated] = useState(false);
  const [restartingPreview, setRestartingPreview] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [now, setNow] = useState(0);

  // Delete dialog
  const [deleteOpen, setDeleteOpen] = useState(false);

  const fetchProject = async () => {
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}`);
      if (!resp.ok) {
        if (resp.status === 404) throw new Error("Project not found");
        throw new Error("Failed to load project details");
      }
      const data: Project = await resp.json();
      setProject(data);
      setName(data.name);
      setDescription(data.description || "");

      // Default repo slug from project name
      const slug = data.name
        .toLowerCase()
        .replace(/[^a-z0-9_-]+/g, "-")
        .replace(/^-+|-+$/g, "");
      setRepoName(slug || `project-${data.id.slice(0, 8)}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const fetchGitStatus = async () => {
    setLoadingGit(true);
    setGitError(null);
    try {
      const [statusRes, projGitRes] = await Promise.all([
        fetch("/api/git/status"),
        fetch(`/api/projects/${encodeURIComponent(projectId)}/git`),
      ]);
      if (statusRes.ok) {
        const s: GitConnectionStatus = await statusRes.json();
        setGitStatus(s);
      }
      if (projGitRes.ok) {
        const p: ProjectGitStatus = await projGitRes.json();
        setProjectGit(p);
      }
    } catch (err: unknown) {
      setGitError(err instanceof Error ? err.message : "Failed to load git status");
    } finally {
      setLoadingGit(false);
    }
  };

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}`);
        if (!resp.ok) {
          if (resp.status === 404) throw new Error("Project not found");
          throw new Error("Failed to load project details");
        }
        const data: Project = await resp.json();
        if (active) {
          setProject(data);
          setName(data.name);
          setDescription(data.description || "");
          const slug = data.name
            .toLowerCase()
            .replace(/[^a-z0-9_-]+/g, "-")
            .replace(/^-+|-+$/g, "");
          setRepoName(slug || `project-${data.id.slice(0, 8)}`);
        }
      } catch (err: unknown) {
        if (active) setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  useEffect(() => {
    if (activeSection !== "git") return;
    let active = true;
    void (async () => {
      try {
        const [statusRes, projGitRes] = await Promise.all([
          fetch("/api/git/status"),
          fetch(`/api/projects/${encodeURIComponent(projectId)}/git`),
        ]);
        if (!active) return;
        if (statusRes.ok) {
          const s: GitConnectionStatus = await statusRes.json();
          setGitStatus(s);
        }
        if (projGitRes.ok) {
          const p: ProjectGitStatus = await projGitRes.json();
          setProjectGit(p);
        }
      } catch (err: unknown) {
        if (active) {
          setGitError(err instanceof Error ? err.message : "Failed to load git status");
        }
      } finally {
        if (active) {
          setLoadingGit(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [activeSection, projectId]);

  const fetchKnowledge = async () => {
    setLoadingKnowledge(true);
    setKnowledgeError(null);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/knowledge`);
      if (!resp.ok) throw new Error("Failed to load project knowledge");
      const data: ProjectKnowledge = await resp.json();
      setKnowledge(data.knowledge || "");
      setKnowledgeUpdatedAt(data.updated_at || null);
    } catch (err: unknown) {
      setKnowledgeError(err instanceof Error ? err.message : "Failed to load knowledge");
    } finally {
      setLoadingKnowledge(false);
    }
  };

  const fetchProjectSkills = async () => {
    setLoadingSkills(true);
    setSkillsError(null);
    try {
      const [projSkillsRes, allSkillsRes] = await Promise.all([
        fetch(`/api/projects/${encodeURIComponent(projectId)}/skills`),
        fetch("/api/skills"),
      ]);
      if (projSkillsRes.ok) {
        const data = await projSkillsRes.json();
        setProjectSkills(data.skills ?? []);
      }
      if (allSkillsRes.ok) {
        const data = await allSkillsRes.json();
        setAllUserSkills(data.skills ?? []);
      }
    } catch (err: unknown) {
      setSkillsError(err instanceof Error ? err.message : "Failed to load skills");
    } finally {
      setLoadingSkills(false);
    }
  };

  const fetchSecrets = async () => {
    setLoadingSecrets(true);
    setSecretsError(null);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/secrets`);
      if (!resp.ok) throw new Error("Failed to load project secrets");
      const data = await resp.json();
      setSecrets(data.secrets ?? []);
    } catch (err: unknown) {
      setSecretsError(err instanceof Error ? err.message : "Failed to load secrets");
    } finally {
      setLoadingSecrets(false);
    }
  };

  useEffect(() => {
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let active = true;
    if (activeSection === "knowledge") {
      void (async () => {
        try {
          const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/knowledge`);
          if (!resp.ok) throw new Error("Failed to load project knowledge");
          const data: ProjectKnowledge = await resp.json();
          if (active) {
            setKnowledge(data.knowledge || "");
            setKnowledgeUpdatedAt(data.updated_at || null);
          }
        } catch (err: unknown) {
          if (active) setKnowledgeError(err instanceof Error ? err.message : "Failed to load knowledge");
        } finally {
          if (active) setLoadingKnowledge(false);
        }
      })();
    } else if (activeSection === "skills") {
      void (async () => {
        try {
          const [projSkillsRes, allSkillsRes] = await Promise.all([
            fetch(`/api/projects/${encodeURIComponent(projectId)}/skills`),
            fetch("/api/skills"),
          ]);
          if (!active) return;
          if (projSkillsRes.ok) {
            const data = await projSkillsRes.json();
            setProjectSkills(data.skills ?? []);
          }
          if (allSkillsRes.ok) {
            const data = await allSkillsRes.json();
            setAllUserSkills(data.skills ?? []);
          }
        } catch (err: unknown) {
          if (active) setSkillsError(err instanceof Error ? err.message : "Failed to load skills");
        } finally {
          if (active) setLoadingSkills(false);
        }
      })();
    } else if (activeSection === "secrets") {
      void (async () => {
        try {
          const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/secrets`);
          if (!resp.ok) throw new Error("Failed to load project secrets");
          const data = await resp.json();
          if (active) {
            setSecrets(data.secrets ?? []);
          }
        } catch (err: unknown) {
          if (active) setSecretsError(err instanceof Error ? err.message : "Failed to load secrets");
        } finally {
          if (active) setLoadingSecrets(false);
        }
      })();
    }
    return () => {
      active = false;
    };
  }, [activeSection, projectId]);

  const handleSaveKnowledge = async (e: FormEvent) => {
    e.preventDefault();
    setSavingKnowledge(true);
    setSavedKnowledgeSuccess(false);
    setKnowledgeError(null);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/knowledge`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ knowledge }),
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to save project knowledge");
      }
      const data: ProjectKnowledge = await resp.json();
      setKnowledge(data.knowledge);
      setKnowledgeUpdatedAt(data.updated_at);
      setSavedKnowledgeSuccess(true);
      setTimeout(() => setSavedKnowledgeSuccess(false), 3000);
    } catch (err: unknown) {
      setKnowledgeError(err instanceof Error ? err.message : "Failed to save knowledge");
    } finally {
      setSavingKnowledge(false);
    }
  };

  const handleAttachSkill = async (skillId: string) => {
    setAttachingSkillId(skillId);
    try {
      const resp = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/skills/${encodeURIComponent(skillId)}`,
        { method: "PUT" },
      );
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to attach skill");
      }
      setAddSkillDialogOpen(false);
      await fetchProjectSkills();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to attach skill");
    } finally {
      setAttachingSkillId(null);
    }
  };

  const handleDetachSkill = async (skillId: string) => {
    setDetachingSkillId(skillId);
    try {
      const resp = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/skills/${encodeURIComponent(skillId)}`,
        { method: "DELETE" },
      );
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to detach skill");
      }
      await fetchProjectSkills();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to detach skill");
    } finally {
      setDetachingSkillId(null);
    }
  };

  const handleSaveGeneral = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setSavedSuccess(false);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), description: description.trim() }),
      });
      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.error || "Failed to update project");
      }
      const updated: Project = await resp.json();
      setProject(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update project");
    } finally {
      setSaving(false);
    }
  };

  const handleArchiveToggle = async () => {
    if (!project) return;
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
        method: "DELETE", // archive toggle
      });
      if (!resp.ok) throw new Error("Failed to archive project");
      fetchProject();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Action failed");
    }
  };

  const handleDelete = async (projId: string, purge: boolean) => {
    const resp = await fetch(`/api/projects/${encodeURIComponent(projId)}?purge=${purge}`, {
      method: "DELETE",
    });
    if (!resp.ok) {
      const errData = await resp.json();
      throw new Error(errData.error || "Failed to delete project");
    }
    router.push("/projects");
  };

  const handleConnectGitHub = async () => {
    setConnectingGit(true);
    setGitError(null);
    setUnconfiguredNotice(null);
    try {
      const res = await fetch("/api/git/github/authorize");
      const data = await res.json();
      if (!res.ok) {
        if (data.code === "not_configured" || res.status === 503) {
          setUnconfiguredNotice(
            "GitHub App is not yet configured on this instance. Set GITHUB_APP_ID, GITHUB_APP_CLIENT_ID, GITHUB_APP_CLIENT_SECRET, and GITHUB_APP_PRIVATE_KEY in your environment to enable GitHub connection.",
          );
          return;
        }
        throw new Error(data.error || "Failed to initiate GitHub authorization");
      }
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err: unknown) {
      setGitError(err instanceof Error ? err.message : "Failed to connect to GitHub");
    } finally {
      setConnectingGit(false);
    }
  };

  const handleDisconnectGitHub = async () => {
    if (
      !confirm(
        "Are you sure you want to disconnect GitHub? Your repository on GitHub will remain completely untouched.",
      )
    ) {
      return;
    }
    setDisconnectingGit(true);
    setGitError(null);
    try {
      const res = await fetch("/api/git/connection", { method: "DELETE" });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.error || "Failed to disconnect");
      }
      await fetchGitStatus();
    } catch (err: unknown) {
      setGitError(err instanceof Error ? err.message : "Failed to disconnect");
    } finally {
      setDisconnectingGit(false);
    }
  };

  const handleCreateRepo = async (e: FormEvent) => {
    e.preventDefault();
    if (!repoName.trim()) return;
    setCreatingRepo(true);
    setGitError(null);
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/git/repo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: repoName.trim(),
          description: description.trim() || undefined,
          private: repoPrivate,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Failed to create GitHub repository");
      }
      setProjectGit(data);
    } catch (err: unknown) {
      setGitError(err instanceof Error ? err.message : "Failed to create repository");
    } finally {
      setCreatingRepo(false);
    }
  };

  const handlePush = async () => {
    setPushingGit(true);
    setGitError(null);
    setPushSuccess(false);
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/git/push`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Failed to push to GitHub");
      }
      setPushSuccess(true);
      setTimeout(() => setPushSuccess(false), 4000);
      await fetchGitStatus();
    } catch (err: unknown) {
      setGitError(err instanceof Error ? err.message : "Push failed");
    } finally {
      setPushingGit(false);
    }
  };

  const handleCopyClone = (cmd: string) => {
    void navigator.clipboard.writeText(cmd);
    setCopiedClone(true);
    setTimeout(() => setCopiedClone(false), 2000);
  };

  const handleRevealSecret = async (key: string) => {
    setRevealingKey(key);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/secrets/reveal/${encodeURIComponent(key)}`, {
        method: "POST",
      });
      if (!resp.ok) throw new Error("Failed to reveal secret");
      const data = await resp.json();
      setRevealedSecrets((prev) => ({
        ...prev,
        [key]: { value: data.value, expiresAt: Date.now() + 30000 },
      }));
    } catch (err: unknown) {
      setSecretsError(err instanceof Error ? err.message : "Failed to reveal secret");
    } finally {
      setRevealingKey(null);
    }
  };

  const handleHideSecret = (key: string) => {
    setRevealedSecrets((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const handleSaveSecret = async (e: FormEvent) => {
    e.preventDefault();
    const key = secretKey.trim().toUpperCase();
    if (!editingSecret && !/^[A-Z][A-Z0-9_]*$/.test(key)) {
      setSecretKeyError("Key must be UPPER_SNAKE_CASE (e.g. STRIPE_API_KEY)");
      return;
    }
    setSavingSecret(true);
    setSecretsError(null);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/secrets/${encodeURIComponent(key)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          value: secretValue,
          description: secretDescription.trim() || undefined,
        }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error || "Failed to save secret");
      }
      setAddSecretOpen(false);
      setSecretsUpdated(true);
      await fetchSecrets();
    } catch (err: unknown) {
      setSecretsError(err instanceof Error ? err.message : "Failed to save secret");
    } finally {
      setSavingSecret(false);
    }
  };

  const handleConfirmDeleteSecret = async () => {
    if (!deleteSecretKey) return;
    setDeletingSecret(true);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/secrets/${encodeURIComponent(deleteSecretKey)}`, {
        method: "DELETE",
      });
      if (!resp.ok) throw new Error("Failed to delete secret");
      setDeleteSecretKey(null);
      setSecretsUpdated(true);
      await fetchSecrets();
    } catch (err: unknown) {
      setSecretsError(err instanceof Error ? err.message : "Failed to delete secret");
    } finally {
      setDeletingSecret(false);
    }
  };

  const handleRestartPreview = async () => {
    setRestartingPreview(true);
    try {
      await fetch(`/api/projects/${encodeURIComponent(projectId)}/preview`, {
        method: "POST",
      });
      setSecretsUpdated(false);
    } catch {
      // Ignored
    } finally {
      setRestartingPreview(false);
    }
  };

  const handleCopySecret = (key: string, text: string) => {
    void navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="mt-6 grid grid-cols-12 gap-8">
          <div className="col-span-3 h-48 animate-pulse rounded bg-muted/30" />
          <div className="col-span-9 h-96 animate-pulse rounded bg-muted/30" />
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h2 className="text-xl font-semibold text-destructive">{error || "Project not found"}</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          This project may have been deleted or belongs to another user account.
        </p>
        <Button asChild className="mt-6">
          <Link href="/projects">Back to projects</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Top Breadcrumb & Return button */}
      <div className="flex items-center justify-between pb-6 border-b">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Link href="/projects" className="hover:underline">Projects</Link>
          <span>/</span>
          <Link href={`/studio/${project.id}`} className="font-medium text-foreground hover:underline">
            {project.name}
          </Link>
          <span>/</span>
          <span>Manage</span>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href={`/studio/${project.id}`} className="gap-2">
            <ArrowLeft className="size-3.5" />
            Back to studio
          </Link>
        </Button>
      </div>

      <div className="mt-8 grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Sub-nav sidebar */}
        <nav className="md:col-span-3 space-y-1" aria-label="Manage sections">
          <button
            type="button"
            onClick={() => setActiveSection("general")}
            className={cn(
              "w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "general"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <Settings className="size-4" />
            General
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("knowledge")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "knowledge"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <BookOpen className="size-4" />
              Knowledge
            </span>
            {knowledge ? (
              <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 border-brand/40 text-brand">
                Active
              </Badge>
            ) : null}
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("skills")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "skills"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <Sparkles className="size-4" />
              Skills
            </span>
            {projectSkills.length > 0 ? (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 font-mono">
                {projectSkills.length}
              </Badge>
            ) : null}
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("secrets")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "secrets"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <Key className="size-4" />
              Secrets
            </span>
            {secrets.length > 0 ? (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 font-mono">
                {secrets.length}
              </Badge>
            ) : null}
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("git")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "git"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <GitBranch className="size-4" />
              Git & GitHub
            </span>
            {projectGit?.repo_full_name ? (
              <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
                Connected
              </Badge>
            ) : null}
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("ai")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "ai"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <Cpu className="size-4" />
              AI & Model
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("seo")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "seo"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <Search className="size-4" />
              SEO & AI Search
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("logs")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "logs"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <Terminal className="size-4" />
              Logs
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("database")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "database"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <Database className="size-4" />
              Database
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("security")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "security"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <ShieldAlert className="size-4" />
              Security
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("tests")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "tests"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <CheckCircle2 className="size-4" />
              Tests
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("publish")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "publish"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <Globe className="size-4" />
              Publish
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("domains")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "domains"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <Globe className="size-4" />
              Domain
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("connectors")}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors",
              activeSection === "connectors"
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
            )}
          >
            <span className="flex items-center gap-2">
              <Plug className="size-4" />
              Connectors
            </span>
          </button>
        </nav>

        {/* Section content */}
        <main className="md:col-span-9 space-y-6">
          {activeSection === "general" ? (
            <>
              {/* General Details Form */}
              <Card>
                <form onSubmit={handleSaveGeneral}>
                  <CardHeader>
                    <CardTitle className="text-lg">General Settings</CardTitle>
                    <CardDescription>
                      Configure your project title and summary description.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-2">
                      <Label htmlFor="proj-name">Project Name</Label>
                      <Input
                        id="proj-name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        disabled={saving}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="proj-desc">Description</Label>
                      <Input
                        id="proj-desc"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Brief description of what this app does"
                        disabled={saving}
                      />
                    </div>
                  </CardContent>
                  <CardFooter className="flex items-center justify-between border-t px-6 py-3">
                    {savedSuccess ? (
                      <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                        <Check className="size-3.5" />
                        Changes saved successfully
                      </span>
                    ) : (
                      <span />
                    )}
                    <Button type="submit" size="sm" disabled={saving || !name.trim()}>
                      {saving ? "Saving..." : "Save changes"}
                    </Button>
                  </CardFooter>
                </form>
              </Card>

              {/* Metadata & Stats */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Project Metadata</CardTitle>
                  <CardDescription>
                    Live metadata, code stats, and accounting ledger totals.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                    <div>
                      <dt className="text-xs font-medium text-muted-foreground">Status</dt>
                      <dd className="mt-1">
                        <Badge variant={project.status === "active" ? "default" : "secondary"}>
                          {project.status}
                        </Badge>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium text-muted-foreground">Credits Spent</dt>
                      <dd className="mt-1 flex items-center gap-1.5 font-medium">
                        <Coins className="size-4 text-amber-500" />
                        {project.credits_spent} credits
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium text-muted-foreground">Created</dt>
                      <dd className="mt-1 text-muted-foreground" title={project.created_at}>
                        {formatDateTime(project.created_at)} ({formatRelativeTime(project.created_at)})
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium text-muted-foreground">Last Updated</dt>
                      <dd className="mt-1 text-muted-foreground" title={project.updated_at}>
                        {formatDateTime(project.updated_at)} ({formatRelativeTime(project.updated_at)})
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium text-muted-foreground">File Count</dt>
                      <dd className="mt-1 flex items-center gap-1.5 font-medium">
                        <FileCode2 className="size-4 text-muted-foreground" />
                        {project.file_count} files
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium text-muted-foreground">Commit SHA</dt>
                      <dd className="mt-1 font-mono text-xs text-muted-foreground">
                        {project.commit_sha ? project.commit_sha.slice(0, 10) : "None"}
                      </dd>
                    </div>
                    <div className="sm:col-span-2">
                      <dt className="text-xs font-medium text-muted-foreground mb-1.5">Entities ({project.entities?.length ?? 0})</dt>
                      <dd className="flex flex-wrap gap-1.5">
                        {project.entities && project.entities.length > 0 ? (
                          project.entities.map((e) => (
                            <Badge key={e} variant="outline" className="px-2 py-0.5 text-xs">
                              {e}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-xs text-muted-foreground">No entities defined</span>
                        )}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>

              {/* Danger Zone */}
              <Card className="border-destructive/30">
                <CardHeader>
                  <CardTitle className="text-lg text-destructive flex items-center gap-2">
                    <ShieldAlert className="size-5" />
                    Danger Zone
                  </CardTitle>
                  <CardDescription>
                    Destructive actions for this project.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between border-t pt-4">
                    <div>
                      <h4 className="text-sm font-medium">Archive Project</h4>
                      <p className="text-xs text-muted-foreground">
                        {project.status === "archived"
                          ? "Restore this project back to the active list."
                          : "Hide this project from your active dashboard."}
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleArchiveToggle}>
                      <Archive className="mr-2 size-3.5" />
                      {project.status === "archived" ? "Unarchive" : "Archive"}
                    </Button>
                  </div>

                  <div className="flex items-center justify-between border-t pt-4">
                    <div>
                      <h4 className="text-sm font-medium text-destructive">Delete Project</h4>
                      <p className="text-xs text-muted-foreground">
                        Permanently delete this project record and optional workspace files.
                      </p>
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setDeleteOpen(true)}
                    >
                      <Trash2 className="mr-2 size-3.5" />
                      Delete project
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : activeSection === "knowledge" ? (
            <>
              {/* Knowledge Section */}
              <Card>
                <form onSubmit={handleSaveKnowledge}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <BookOpen className="size-4 text-brand" />
                          Project Knowledge
                        </CardTitle>
                        <CardDescription>
                          Persistent brief and domain context injected into every build and edit of this project.
                        </CardDescription>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        Applied to every message
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {knowledgeError && (
                      <div
                        role="alert"
                        className="flex gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                      >
                        <AlertCircle className="mt-0.5 size-4 shrink-0" />
                        {knowledgeError}
                      </div>
                    )}

                    <div className="grid gap-2">
                      <div className="flex items-center justify-between">
                        <Label htmlFor="project-knowledge">Knowledge Brief</Label>
                        <span
                          className={cn(
                            "text-xs tabular-nums",
                            knowledge.length > 16384 ? "text-destructive font-semibold" : "text-muted-foreground"
                          )}
                        >
                          {knowledge.length.toLocaleString()} / 16,384 chars
                        </span>
                      </div>
                      <textarea
                        id="project-knowledge"
                        value={knowledge}
                        onChange={(e) => setKnowledge(e.target.value)}
                        placeholder="Define background context, architectural principles, domain entities, or business rules for this project..."
                        rows={12}
                        disabled={loadingKnowledge || savingKnowledge}
                        className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                      />
                      <p className="text-xs text-muted-foreground">
                        Project knowledge is always prioritized over skills when assembling prompt context.
                      </p>
                    </div>
                  </CardContent>
                  <CardFooter className="flex items-center justify-between border-t px-6 py-3">
                    <div className="flex items-center gap-2">
                      {savedKnowledgeSuccess ? (
                        <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                          <Check className="size-3.5" />
                          Knowledge saved successfully
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          {knowledgeUpdatedAt
                            ? `Saved ${formatRelativeTime(knowledgeUpdatedAt)}`
                            : "Never saved"}
                        </span>
                      )}
                    </div>
                    <Button
                      type="submit"
                      size="sm"
                      disabled={savingKnowledge || loadingKnowledge || knowledge.length > 16384}
                    >
                      {savingKnowledge ? (
                        <>
                          <LoaderCircle className="size-3.5 animate-spin mr-1.5" />
                          Saving...
                        </>
                      ) : (
                        "Save knowledge"
                      )}
                    </Button>
                  </CardFooter>
                </form>
              </Card>
            </>
          ) : activeSection === "skills" ? (
            <>
              {/* Skills Section */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Sparkles className="size-4 text-brand" />
                        Project Skills
                      </CardTitle>
                      <CardDescription>
                        Custom instruction sets attached to this project and applied to each build.
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setAddSkillDialogOpen(true)}
                        className="gap-1.5"
                      >
                        <Plus className="size-3.5" />
                        Add from library
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => setNewSkillDialogOpen(true)}
                        className="gap-1.5"
                      >
                        <Plus className="size-3.5" />
                        New skill
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {skillsError && (
                    <div
                      role="alert"
                      className="flex gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                    >
                      <AlertCircle className="mt-0.5 size-4 shrink-0" />
                      {skillsError}
                    </div>
                  )}

                  {loadingSkills ? (
                    <div className="flex items-center justify-center py-10 text-muted-foreground">
                      <LoaderCircle className="size-5 animate-spin mr-2" />
                      Loading project skills...
                    </div>
                  ) : projectSkills.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-border/80 p-8 text-center">
                      <Sparkles className="mx-auto size-8 text-muted-foreground/60" />
                      <h3 className="mt-2 text-sm font-semibold">No skills attached yet</h3>
                      <p className="mt-1 text-xs text-muted-foreground max-w-sm mx-auto">
                        Attach skills from your library or create new ones to guide this project&apos;s code style and rules.
                      </p>
                      <div className="mt-4 flex items-center justify-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setAddSkillDialogOpen(true)}
                          className="gap-1.5"
                        >
                          <Plus className="size-3.5" />
                          Add from library
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => setNewSkillDialogOpen(true)}
                          className="gap-1.5"
                        >
                          <Plus className="size-3.5" />
                          Create new skill
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {projectSkills.map((skill) => (
                        <Card key={skill.id} size="sm" className="flex flex-col justify-between">
                          <CardHeader className="pb-2">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <CardTitle className="truncate text-sm font-semibold">{skill.title}</CardTitle>
                                <span className="font-mono text-xs text-brand font-medium">@{skill.name}</span>
                              </div>
                              {skill.is_default && (
                                <Badge variant="secondary" className="text-[10px] uppercase tracking-wider shrink-0">
                                  Default
                                </Badge>
                              )}
                            </div>
                            {skill.description && (
                              <CardDescription className="line-clamp-2 text-xs mt-1">
                                {skill.description}
                              </CardDescription>
                            )}
                          </CardHeader>
                          <CardContent className="pt-0 pb-2">
                            <div className="rounded bg-muted/50 p-2 font-mono text-[11px] text-muted-foreground line-clamp-3">
                              {skill.body}
                            </div>
                          </CardContent>
                          <CardFooter className="pt-2 border-t flex items-center justify-between text-xs text-muted-foreground">
                            <span>{skill.body.length.toLocaleString()} chars</span>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 text-xs text-destructive hover:text-destructive gap-1 px-2"
                              disabled={detachingSkillId === skill.id}
                              onClick={() => handleDetachSkill(skill.id)}
                            >
                              {detachingSkillId === skill.id ? (
                                <LoaderCircle className="size-3 animate-spin" />
                              ) : (
                                <Unlink className="size-3" />
                              )}
                              Detach
                            </Button>
                          </CardFooter>
                        </Card>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Add From Library Dialog */}
              <Dialog open={addSkillDialogOpen} onOpenChange={setAddSkillDialogOpen}>
                <DialogContent className="sm:max-w-lg">
                  <DialogHeader>
                    <DialogTitle>Add Skill from Library</DialogTitle>
                    <DialogDescription>
                      Select an existing skill from your account library to attach to this project.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="max-h-[60vh] overflow-y-auto space-y-2 py-2">
                    {allUserSkills.filter((s) => !projectSkills.some((ps) => ps.id === s.id)).length === 0 ? (
                      <div className="py-6 text-center text-xs text-muted-foreground">
                        All skills in your library are already attached, or no skills exist yet.
                      </div>
                    ) : (
                      allUserSkills
                        .filter((s) => !projectSkills.some((ps) => ps.id === s.id))
                        .map((skill) => (
                          <div
                            key={skill.id}
                            className="flex items-center justify-between p-3 rounded-lg border border-border/70 hover:bg-muted/30 transition-colors"
                          >
                            <div className="min-w-0 pr-3">
                              <h4 className="text-sm font-medium truncate">{skill.title}</h4>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="font-mono text-xs text-brand">@{skill.name}</span>
                                {skill.description && (
                                  <span className="text-xs text-muted-foreground truncate max-w-xs">
                                    · {skill.description}
                                  </span>
                                )}
                              </div>
                            </div>
                            <Button
                              size="sm"
                              disabled={attachingSkillId === skill.id}
                              onClick={() => handleAttachSkill(skill.id)}
                            >
                              {attachingSkillId === skill.id ? (
                                <LoaderCircle className="size-3.5 animate-spin" />
                              ) : (
                                "Attach"
                              )}
                            </Button>
                          </div>
                        ))
                    )}
                  </div>
                  <DialogFooter className="border-t pt-3">
                    <Button variant="outline" onClick={() => setAddSkillDialogOpen(false)}>
                      Close
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              {/* New Skill Shortcut Dialog */}
              <SkillEditorDialog
                open={newSkillDialogOpen}
                onOpenChange={setNewSkillDialogOpen}
                skill={null}
                onSaved={async () => {
                  setNewSkillDialogOpen(false);
                  await fetchProjectSkills();
                }}
              />
            </>
          ) : activeSection === "secrets" ? (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold tracking-tight">Environment Secrets</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    Encrypted environment variables injected into preview and deployment processes.
                  </p>
                </div>
                <Button
                  onClick={() => {
                    setSecretKey("");
                    setSecretValue("");
                    setSecretDescription("");
                    setSecretKeyError(null);
                    setEditingSecret(false);
                    setAddSecretOpen(true);
                  }}
                  size="sm"
                  className="gap-2 shrink-0"
                >
                  <Plus className="size-4" />
                  Add secret
                </Button>
              </div>

              {secretsUpdated ? (
                <div className="flex items-center justify-between gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3.5 text-sm text-amber-700 dark:text-amber-400">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="size-4 shrink-0" />
                    <span>Secrets have been updated. Restart the preview to apply changes.</span>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-amber-500/30 hover:bg-amber-500/20 text-xs h-7 gap-1.5"
                    onClick={handleRestartPreview}
                    disabled={restartingPreview}
                  >
                    <RefreshCw className={cn("size-3", restartingPreview && "animate-spin")} />
                    Restart preview
                  </Button>
                </div>
              ) : null}

              {secretsError ? (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex items-start gap-3">
                  <AlertCircle className="size-5 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-semibold">Error</p>
                    <p className="mt-1 text-xs font-mono">{secretsError}</p>
                  </div>
                </div>
              ) : null}

              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/40 p-2.5 rounded-md border border-border/50">
                    <ShieldAlert className="size-4 text-brand shrink-0" />
                    <span>
                      Stored encrypted with AES-256-GCM. Injected directly into your app&apos;s runtime environment when it runs or deploys. Never written into your source code or repository.
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  {loadingSecrets ? (
                    <div className="space-y-2 py-4">
                      <div className="h-10 animate-pulse rounded bg-muted/50" />
                      <div className="h-10 animate-pulse rounded bg-muted/50" />
                    </div>
                  ) : secrets.length === 0 ? (
                    <div className="py-12 text-center">
                      <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-muted/50 text-muted-foreground mb-3">
                        <Key className="size-6" />
                      </div>
                      <h3 className="text-sm font-medium text-foreground">No secrets configured</h3>
                      <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                        Add environment variables such as <code className="font-mono">STRIPE_SECRET_KEY</code> or <code className="font-mono">SMTP_PASSWORD</code> that your app needs at runtime.
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-4 gap-2"
                        onClick={() => {
                          setSecretKey("");
                          setSecretValue("");
                          setSecretDescription("");
                          setSecretKeyError(null);
                          setEditingSecret(false);
                          setAddSecretOpen(true);
                        }}
                      >
                        <Plus className="size-3.5" />
                        Add your first secret
                      </Button>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left text-xs font-medium text-muted-foreground">
                            <th className="pb-2.5 font-medium">Key</th>
                            <th className="pb-2.5 font-medium">Value</th>
                            <th className="pb-2.5 font-medium">Description</th>
                            <th className="pb-2.5 font-medium">Updated</th>
                            <th className="pb-2.5 font-medium text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40">
                          {secrets.map((s) => {
                            const isRevealed = Boolean(revealedSecrets[s.key]);
                            const revealed = revealedSecrets[s.key];
                            const remainingSeconds = revealed ? Math.max(0, Math.ceil((revealed.expiresAt - now) / 1000)) : 0;
                            return (
                              <tr key={s.key} className="group hover:bg-muted/20">
                                <td className="py-3 pr-4 font-mono text-xs font-semibold text-foreground">
                                  <div className="flex items-center gap-1.5">
                                    <span>{s.key}</span>
                                    <button
                                      type="button"
                                      onClick={() => handleCopySecret(s.key, s.key)}
                                      className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-foreground transition-opacity"
                                      title="Copy key"
                                    >
                                      {copiedKey === s.key ? <Check className="size-3 text-emerald-500" /> : <Copy className="size-3" />}
                                    </button>
                                  </div>
                                </td>
                                <td className="py-3 pr-4 font-mono text-xs">
                                  <div className="flex items-center gap-2">
                                    {isRevealed ? (
                                      <>
                                        <span className="bg-muted px-2 py-0.5 rounded text-foreground max-w-[200px] truncate">
                                          {revealed?.value}
                                        </span>
                                        <span className="text-[10px] text-amber-600 dark:text-amber-400 font-sans">
                                          ({remainingSeconds}s)
                                        </span>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                                          onClick={() => handleHideSecret(s.key)}
                                          title="Hide value"
                                        >
                                          <EyeOff className="size-3.5" />
                                        </Button>
                                      </>
                                    ) : (
                                      <>
                                        <span className="text-muted-foreground tracking-widest">••••••••</span>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                                          onClick={() => handleRevealSecret(s.key)}
                                          disabled={revealingKey === s.key}
                                          title="Show value (30s)"
                                        >
                                          {revealingKey === s.key ? (
                                            <LoaderCircle className="size-3.5 animate-spin" />
                                          ) : (
                                            <Eye className="size-3.5" />
                                          )}
                                        </Button>
                                      </>
                                    )}
                                  </div>
                                </td>
                                <td className="py-3 pr-4 text-xs text-muted-foreground max-w-[200px] truncate">
                                  {s.description || "—"}
                                </td>
                                <td className="py-3 pr-4 text-xs text-muted-foreground whitespace-nowrap">
                                  {s.updated_at ? formatRelativeTime(s.updated_at) : "—"}
                                </td>
                                <td className="py-3 text-right whitespace-nowrap">
                                  <div className="flex items-center justify-end gap-1">
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 px-2 text-xs"
                                      onClick={() => {
                                        setSecretKey(s.key);
                                        setSecretValue("");
                                        setSecretDescription(s.description);
                                        setSecretKeyError(null);
                                        setEditingSecret(true);
                                        setAddSecretOpen(true);
                                      }}
                                    >
                                      Edit
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                                      onClick={() => setDeleteSecretKey(s.key)}
                                    >
                                      Delete
                                    </Button>
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Add/Edit Secret Dialog */}
              <Dialog open={addSecretOpen} onOpenChange={setAddSecretOpen}>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader>
                    <DialogTitle>{editingSecret ? `Edit secret: ${secretKey}` : "Add environment secret"}</DialogTitle>
                    <DialogDescription>
                      {editingSecret
                        ? "Update the secret value or description. Key cannot be changed."
                        : "Set an environment variable that will be encrypted and available to your application at runtime."}
                    </DialogDescription>
                  </DialogHeader>
                  <form onSubmit={handleSaveSecret} className="space-y-4 py-2">
                    {!editingSecret ? (
                      <div className="space-y-1.5">
                        <Label htmlFor="secret-key">Key Name</Label>
                        <Input
                          id="secret-key"
                          placeholder="e.g. STRIPE_API_KEY"
                          value={secretKey}
                          onChange={(e) => {
                            const val = e.target.value.toUpperCase();
                            setSecretKey(val);
                            if (val && !/^[A-Z][A-Z0-9_]*$/.test(val)) {
                              setSecretKeyError("Must be UPPER_SNAKE_CASE (starts with A-Z, only A-Z, 0-9, and _)");
                            } else {
                              setSecretKeyError(null);
                            }
                          }}
                          className="font-mono text-xs uppercase"
                          required
                        />
                        {secretKeyError ? (
                          <p className="text-[11px] text-destructive">{secretKeyError}</p>
                        ) : (
                          <p className="text-[11px] text-muted-foreground">
                            Use UPPER_SNAKE_CASE. Maps directly to process.env in your app.
                          </p>
                        )}
                      </div>
                    ) : null}

                    <div className="space-y-1.5">
                      <Label htmlFor="secret-val">{editingSecret ? "New Value (leave blank to keep current)" : "Secret Value"}</Label>
                      <Input
                        id="secret-val"
                        type="password"
                        placeholder={editingSecret ? "••••••••" : "Paste secret value"}
                        value={secretValue}
                        onChange={(e) => setSecretValue(e.target.value)}
                        className="font-mono text-xs"
                        required={!editingSecret}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label htmlFor="secret-desc">Description (optional)</Label>
                      <Input
                        id="secret-desc"
                        placeholder="e.g. Stripe production publishable/secret key"
                        value={secretDescription}
                        onChange={(e) => setSecretDescription(e.target.value)}
                        className="text-xs"
                      />
                    </div>

                    <div className="rounded-md bg-muted/40 p-2.5 text-[11px] text-muted-foreground border border-border/50">
                      Stored encrypted (AES-256-GCM). Used when your app runs and when you publish it. Never written into your code or git.
                    </div>

                    <DialogFooter className="gap-2 sm:gap-0 pt-2">
                      <Button type="button" variant="outline" onClick={() => setAddSecretOpen(false)} disabled={savingSecret}>
                        Cancel
                      </Button>
                      <Button type="submit" disabled={savingSecret || (!editingSecret && Boolean(secretKeyError))}>
                        {savingSecret ? (
                          <>
                            <LoaderCircle className="size-3.5 animate-spin mr-1.5" />
                            Saving...
                          </>
                        ) : (
                          "Save secret"
                        )}
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>

              {/* Delete Secret Confirmation Dialog */}
              <Dialog open={Boolean(deleteSecretKey)} onOpenChange={(open) => !open && setDeleteSecretKey(null)}>
                <DialogContent className="sm:max-w-sm">
                  <DialogHeader>
                    <DialogTitle>Delete secret</DialogTitle>
                    <DialogDescription>
                      Are you sure you want to delete <code className="font-mono font-semibold text-foreground">{deleteSecretKey}</code>? Any running or future app instances relying on this secret will no longer have access to it.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter className="gap-2 sm:gap-0 pt-2">
                    <Button variant="outline" onClick={() => setDeleteSecretKey(null)} disabled={deletingSecret}>
                      Cancel
                    </Button>
                    <Button variant="destructive" onClick={handleConfirmDeleteSecret} disabled={deletingSecret}>
                      {deletingSecret ? (
                        <>
                          <LoaderCircle className="size-3.5 animate-spin mr-1.5" />
                          Deleting...
                        </>
                      ) : (
                        "Delete secret"
                      )}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          ) : activeSection === "ai" ? (
            <ProjectAIManage projectId={projectId} />
          ) : activeSection === "seo" ? (
            <ProjectSEOManage projectId={projectId} projectName={project.name} />
          ) : activeSection === "logs" ? (
            <ProjectLogsManage projectId={projectId} />
          ) : activeSection === "database" ? (
            <ProjectDbManage projectId={projectId} />
          ) : activeSection === "security" ? (
            <ProjectSecurityManage projectId={projectId} />
          ) : activeSection === "tests" ? (
            <ProjectTestsManage projectId={projectId} />
          ) : activeSection === "publish" ? (
            <ProjectPublishManage projectId={projectId} projectName={project?.name || "Project"} />
          ) : activeSection === "domains" ? (
            <ProjectDomainManage projectId={projectId} projectName={project?.name || "Project"} />
          ) : activeSection === "connectors" ? (
            <ProjectConnectorsManage projectId={projectId} projectName={project?.name || "Project"} />
          ) : (
            <>
              {/* Git & GitHub Section */}
              {unconfiguredNotice ? (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-300 flex items-start gap-3">
                  <AlertCircle className="size-5 shrink-0 text-amber-500 mt-0.5" />
                  <div>
                    <p className="font-semibold">GitHub Integration Notice</p>
                    <p className="mt-1 text-xs leading-relaxed opacity-90">{unconfiguredNotice}</p>
                  </div>
                </div>
              ) : null}

              {gitError ? (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex items-start gap-3">
                  <AlertCircle className="size-5 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-semibold">Error</p>
                    <p className="mt-1 text-xs font-mono">{gitError}</p>
                  </div>
                </div>
              ) : null}

              {/* State 1: Not connected to GitHub */}
              {!gitStatus?.connected ? (
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2">
                      <GithubIcon className="size-5" />
                      <CardTitle className="text-lg">Connect GitHub</CardTitle>
                    </div>
                    <CardDescription className="text-sm pt-1">
                      Your code is a real git repository. Connect GitHub to own it.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      Connecting your GitHub account lets you export full repositories, sync revisions
                      with one click, and deploy directly to Vercel or Netlify without lock-in. Every
                      agent build and edit is committed with clean history.
                    </p>

                    <div className="flex flex-wrap items-center gap-3 pt-2">
                      <Button
                        onClick={handleConnectGitHub}
                        disabled={connectingGit}
                        className="gap-2"
                      >
                        {connectingGit ? (
                          <LoaderCircle className="size-4 animate-spin" />
                        ) : (
                          <GithubIcon className="size-4" />
                        )}
                        Connect GitHub
                      </Button>
                      <Button asChild variant="outline" className="gap-2">
                        <a href={`/api/projects/${encodeURIComponent(projectId)}/export`} download>
                          <Download className="size-4" />
                          Download .zip (No account needed)
                        </a>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : null}

              {/* State 2: Connected, but no repo created for this project */}
              {gitStatus?.connected && !projectGit?.repo_full_name ? (
                <div className="space-y-6">
                  {/* Account chip banner */}
                  <div className="flex items-center justify-between rounded-lg border bg-card p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex size-9 items-center justify-center rounded-full bg-secondary">
                        <GithubIcon className="size-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold">@{gitStatus.external_login}</span>
                          <Badge variant="outline" className="text-[10px] text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                            Connected
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Authorized via GitHub App
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleDisconnectGitHub}
                      disabled={disconnectingGit}
                      className="text-xs text-muted-foreground hover:text-destructive gap-1.5"
                    >
                      {disconnectingGit ? (
                        <LoaderCircle className="size-3 animate-spin" />
                      ) : (
                        <Unlink className="size-3" />
                      )}
                      Disconnect
                    </Button>
                  </div>

                  {/* Create Repository Form */}
                  <Card>
                    <form onSubmit={handleCreateRepo}>
                      <CardHeader>
                        <CardTitle className="text-lg">Create GitHub Repository</CardTitle>
                        <CardDescription>
                          Create a new repository under @{gitStatus.external_login} and push this workspace.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid gap-2">
                          <Label htmlFor="repo-name">Repository Name</Label>
                          <Input
                            id="repo-name"
                            value={repoName}
                            onChange={(e) => setRepoName(e.target.value)}
                            placeholder="my-cool-app"
                            required
                            disabled={creatingRepo}
                          />
                        </div>

                        <div className="grid gap-2">
                          <Label>Visibility</Label>
                          <div className="flex items-center gap-4 pt-1">
                            <label className="flex items-center gap-2 cursor-pointer text-sm">
                              <input
                                type="radio"
                                name="visibility"
                                checked={repoPrivate}
                                onChange={() => setRepoPrivate(true)}
                                className="accent-primary"
                              />
                              <Lock className="size-3.5 text-muted-foreground" />
                              <span>Private (Recommended)</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer text-sm">
                              <input
                                type="radio"
                                name="visibility"
                                checked={!repoPrivate}
                                onChange={() => setRepoPrivate(false)}
                                className="accent-primary"
                              />
                              <span>Public</span>
                            </label>
                          </div>
                        </div>
                      </CardContent>
                      <CardFooter className="flex items-center justify-between border-t px-6 py-3">
                        <Button asChild variant="ghost" size="sm">
                          <a href={`/api/projects/${encodeURIComponent(projectId)}/export`} download className="gap-1.5 text-xs text-muted-foreground">
                            <Download className="size-3.5" />
                            Download .zip instead
                          </a>
                        </Button>
                        <Button type="submit" size="sm" disabled={creatingRepo || !repoName.trim()} className="gap-2">
                          {creatingRepo ? (
                            <>
                              <LoaderCircle className="size-3.5 animate-spin" />
                              Creating repository...
                            </>
                          ) : (
                            <>
                              <GithubIcon className="size-3.5" />
                              Create repository
                            </>
                          )}
                        </Button>
                      </CardFooter>
                    </form>
                  </Card>
                </div>
              ) : null}

              {/* State 3: Connected with a repo */}
              {gitStatus?.connected && projectGit?.repo_full_name ? (
                <div className="space-y-6">
                  {/* Account & Repo Banner */}
                  <Card>
                    <CardHeader className="pb-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2.5">
                          <GithubIcon className="size-5" />
                          <CardTitle className="text-lg">GitHub Repository</CardTitle>
                          <Badge variant="outline" className="text-xs">
                            {projectGit.repo_private ? "Private" : "Public"}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">@{gitStatus.external_login}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleDisconnectGitHub}
                            disabled={disconnectingGit}
                            className="h-7 text-xs text-muted-foreground hover:text-destructive"
                          >
                            Disconnect
                          </Button>
                        </div>
                      </div>
                      <CardDescription className="pt-1">
                        Linked repository for revisions and automated deployments.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex items-center justify-between rounded-md border bg-muted/30 p-3">
                        <div className="flex items-center gap-2 truncate font-mono text-sm">
                          <span className="font-semibold text-foreground">{projectGit.repo_full_name}</span>
                        </div>
                        {projectGit.repo_url ? (
                          <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs shrink-0">
                            <a href={projectGit.repo_url} target="_blank" rel="noopener noreferrer">
                              View on GitHub
                              <ExternalLink className="size-3" />
                            </a>
                          </Button>
                        ) : null}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Sync & Push Card */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Sync & Push</CardTitle>
                      <CardDescription>
                        Push new workspace commits to your GitHub repository.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <dl className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                        <div className="rounded-md border p-3">
                          <dt className="text-xs font-medium text-muted-foreground">Branch</dt>
                          <dd className="mt-1 font-mono text-sm font-semibold">{projectGit.branch || "main"}</dd>
                        </div>
                        <div className="rounded-md border p-3">
                          <dt className="text-xs font-medium text-muted-foreground">Last Pushed</dt>
                          <dd className="mt-1 font-mono text-xs text-muted-foreground truncate">
                            {projectGit.last_pushed_sha ? (
                              <>
                                <span className="font-semibold text-foreground">{projectGit.last_pushed_sha.slice(0, 7)}</span>
                                {projectGit.last_pushed_at ? ` · ${formatRelativeTime(projectGit.last_pushed_at)}` : ""}
                              </>
                            ) : (
                              "Not pushed yet"
                            )}
                          </dd>
                        </div>
                        <div className="rounded-md border p-3">
                          <dt className="text-xs font-medium text-muted-foreground">Sync Status</dt>
                          <dd className="mt-1">
                            {projectGit.ahead_by && projectGit.ahead_by > 0 ? (
                              <Badge variant="outline" className="text-amber-500 border-amber-500/30">
                                {projectGit.ahead_by} {projectGit.ahead_by === 1 ? "commit" : "commits"} ahead
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                                Up to date
                              </Badge>
                            )}
                          </dd>
                        </div>
                      </dl>

                      {pushSuccess ? (
                        <div className="flex items-center gap-2 rounded-md bg-emerald-500/10 border border-emerald-500/30 p-3 text-sm text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="size-4 shrink-0" />
                          <span>Pushed successfully to GitHub!</span>
                        </div>
                      ) : null}
                    </CardContent>
                    <CardFooter className="flex items-center justify-between border-t px-6 py-3">
                      <Button asChild variant="ghost" size="sm">
                        <a href={`/api/projects/${encodeURIComponent(projectId)}/export`} download className="gap-1.5 text-xs text-muted-foreground">
                          <Download className="size-3.5" />
                          Download .zip
                        </a>
                      </Button>
                      <Button
                        onClick={handlePush}
                        disabled={pushingGit}
                        size="sm"
                        className="gap-2"
                      >
                        {pushingGit ? (
                          <>
                            <LoaderCircle className="size-3.5 animate-spin" />
                            Pushing to GitHub...
                          </>
                        ) : (
                          <>
                            <RefreshCw className="size-3.5" />
                            Push to GitHub
                          </>
                        )}
                      </Button>
                    </CardFooter>
                  </Card>

                  {/* Clone command Card */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Clone Locally</CardTitle>
                      <CardDescription>
                        Run this command in your terminal to clone this repository to your computer.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center justify-between gap-3 rounded-md bg-muted/60 px-3.5 py-2.5 font-mono text-xs text-foreground">
                        <code className="truncate">git clone {projectGit.repo_url}</code>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopyClone(`git clone ${projectGit.repo_url}`)}
                          className="h-7 px-2 text-xs shrink-0"
                        >
                          {copiedClone ? (
                            <Check className="size-3.5 text-green-500" />
                          ) : (
                            <Copy className="size-3.5" />
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ) : null}

              {/* Free, no-account path card (always present) */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Instant Download</CardTitle>
                  <CardDescription>
                    Export an unpolluted .zip archive of this workspace without Git or external services.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    The archive excludes internal Git metadata, node_modules, build caches, and secret
                    environment variables (preserving .env.example). Ready to run locally with{" "}
                    <code className="rounded bg-muted px-1 py-0.5 font-mono">pnpm install && pnpm build</code>.
                  </p>
                  <div className="pt-2">
                    <Button asChild variant="outline" size="sm" className="gap-2">
                      <a href={`/api/projects/${encodeURIComponent(projectId)}/export`} download>
                        <Download className="size-3.5" />
                        Download project (.zip)
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </main>
      </div>

      <DeleteDialog
        project={project}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onDelete={handleDelete}
      />
    </div>
  );
}
