"use client";

import { use, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Archive,
  ArrowLeft,
  Check,
  CheckCircle2,
  Coins,
  Copy,
  Download,
  ExternalLink,
  FileCode2,
  GitBranch,
  LoaderCircle,
  Lock,
  RefreshCw,
  Settings,
  ShieldAlert,
  Trash2,
  Unlink,
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
} from "@/lib/control-plane";
import { formatDateTime, formatRelativeTime } from "@/lib/time";
import { DeleteDialog } from "@/components/project-dialogs";
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

  // Section nav: "general" | "git"
  const [activeSection, setActiveSection] = useState<"general" | "git">("general");

  // General Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

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
