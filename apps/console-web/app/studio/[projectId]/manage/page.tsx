"use client";

import { use, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Archive,
  ArrowLeft,
  Calendar,
  Check,
  Coins,
  FileCode2,
  GitCommit,
  Layers,
  LoaderCircle,
  Settings,
  ShieldAlert,
  Trash2,
} from "lucide-react";
import type { Project } from "@/lib/control-plane";
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

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
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
            className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md bg-secondary text-secondary-foreground"
          >
            <Settings className="size-4" />
            General
          </button>
        </nav>

        {/* Section content */}
        <main className="md:col-span-9 space-y-6">
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
