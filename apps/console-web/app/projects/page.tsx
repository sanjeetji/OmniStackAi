"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Archive,
  ArrowUpDown,
  Copy,
  FolderTree,
  MoreVertical,
  Pencil,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import type { Project } from "@/lib/control-plane";
import AppShell from "@/components/app-shell";
import ProjectCard from "@/components/project-card";
import { DeleteDialog, RenameDialog } from "@/components/project-dialogs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters and sorting
  const [statusFilter, setStatusFilter] = useState<"active" | "archived">("active");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"updated" | "created" | "name">("updated");

  // Dialogs
  const [renameProject, setRenameProject] = useState<Project | null>(null);
  const [deleteProject, setDeleteProject] = useState<Project | null>(null);

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/projects?status=${statusFilter}&sort=${sortBy}`);
      if (!resp.ok) {
        throw new Error("Could not load projects");
      }
      const data = await resp.json();
      setProjects(data.projects ?? []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const resp = await fetch(`/api/projects?status=${statusFilter}&sort=${sortBy}`);
        if (!resp.ok) throw new Error("Could not load projects");
        const data = await resp.json();
        if (active) {
          setProjects(data.projects ?? []);
          setError(null);
        }
      } catch (err: unknown) {
        if (active) setError(err instanceof Error ? err.message : "Failed to load projects");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [statusFilter, sortBy]);

  const filteredProjects = useMemo(() => {
    if (!searchQuery.trim()) return projects;
    const q = searchQuery.toLowerCase().trim();
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q)) ||
        (p.last_prompt && p.last_prompt.toLowerCase().includes(q)) ||
        (p.entities && p.entities.some((e) => e.toLowerCase().includes(q)))
    );
  }, [projects, searchQuery]);

  const handleRename = async (projectId: string, newName: string, newDescription?: string) => {
    const resp = await fetch(`/api/projects/${projectId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName, description: newDescription }),
    });
    if (!resp.ok) {
      const errData = await resp.json();
      throw new Error(errData.error || "Failed to rename project");
    }
    fetchProjects();
  };

  const handleArchive = async (project: Project) => {
    const resp = await fetch(`/api/projects/${project.id}`, {
      method: "DELETE",
    });
    if (resp.ok) {
      fetchProjects();
    }
  };

  const handleDelete = async (projectId: string, purge: boolean) => {
    const resp = await fetch(`/api/projects/${projectId}?purge=${purge}`, {
      method: "DELETE",
    });
    if (!resp.ok) {
      const errData = await resp.json();
      throw new Error(errData.error || "Failed to delete project");
    }
    fetchProjects();
  };

  const handleDuplicate = async (project: Project) => {
    try {
      const resp = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: `${project.name} (Copy)`,
          description: project.description,
          prompt: project.last_prompt,
        }),
      });
      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.error || "Failed to duplicate project");
      }
      fetchProjects();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to duplicate project");
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Manage your apps, workspaces, and code generations.
          </p>
        </div>
        <Button asChild>
          <Link href="/studio" className="gap-2">
            <Plus className="size-4" />
            New app
          </Link>
        </Button>
      </div>

      {/* Toolbar: Search, Status tabs, Sort */}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-3">
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 text-sm"
            />
          </div>
          <Tabs
            value={statusFilter}
            onValueChange={(val) => setStatusFilter(val as "active" | "archived")}
            className="w-auto"
          >
            <TabsList>
              <TabsTrigger value="active">Active</TabsTrigger>
              <TabsTrigger value="archived">Archived</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as "updated" | "created" | "name")}
            className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="updated">Last updated</option>
            <option value="created">Created</option>
            <option value="name">Name</option>
          </select>
        </div>
      </div>

      {/* Project Grid */}
      <div className="mt-6">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-44 animate-pulse rounded-lg border bg-muted/40" />
            ))}
          </div>
        ) : error ? (
          <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-6 text-center text-sm text-destructive">
            {error}
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="rounded-lg border border-dashed p-12 text-center">
            <FolderTree className="mx-auto size-10 text-muted-foreground/60" />
            <h3 className="mt-4 text-base font-semibold">
              {searchQuery
                ? "No matching projects"
                : statusFilter === "archived"
                ? "No archived projects"
                : "No projects yet"}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {searchQuery
                ? "Try adjusting your search query."
                : statusFilter === "archived"
                ? "Archived projects will appear here."
                : "Describe what you want to build to start your first project."}
            </p>
            {!searchQuery && statusFilter === "active" && (
              <Button asChild className="mt-4">
                <Link href="/studio">Start building</Link>
              </Button>
            )}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onRename={setRenameProject}
                onArchive={handleArchive}
                onDelete={setDeleteProject}
              />
            ))}
          </div>
        )}
      </div>

      <RenameDialog
        project={renameProject}
        open={Boolean(renameProject)}
        onOpenChange={(open) => !open && setRenameProject(null)}
        onRename={handleRename}
      />

      <DeleteDialog
        project={deleteProject}
        open={Boolean(deleteProject)}
        onOpenChange={(open) => !open && setDeleteProject(null)}
        onDelete={handleDelete}
      />
    </div>
  );
}
