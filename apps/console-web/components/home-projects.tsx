"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, FolderTree, LoaderCircle } from "lucide-react";
import type { Project } from "@/lib/control-plane";
import ProjectCard from "./project-card";
import { DeleteDialog, RenameDialog } from "./project-dialogs";
import { Button } from "./ui/button";

export default function HomeProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [renameProject, setRenameProject] = useState<Project | null>(null);
  const [deleteProject, setDeleteProject] = useState<Project | null>(null);

  const fetchProjects = async () => {
    try {
      const resp = await fetch("/api/projects?status=active&sort=updated&limit=6");
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
        const resp = await fetch("/api/projects?status=active&sort=updated&limit=6");
        if (!resp.ok) throw new Error("Could not load projects");
        const data = await resp.json();
        if (active) setProjects(data.projects ?? []);
      } catch (err: unknown) {
        if (active) setError(err instanceof Error ? err.message : "Failed to load projects");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

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
    const newStatus = project.status === "archived" ? "active" : "archived";
    const resp = await fetch(`/api/projects/${project.id}`, {
      method: "DELETE", // archive by default
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

  if (loading) {
    return (
      <div className="mt-8">
        <div className="flex items-center justify-between pb-3">
          <div className="h-6 w-32 animate-pulse rounded bg-muted" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 animate-pulse rounded-lg border bg-muted/40" />
          ))}
        </div>
      </div>
    );
  }

  if (error || projects.length === 0) {
    // Empty state: let the page continue to the getting-started guide
    return null;
  }

  return (
    <section aria-labelledby="your-projects-heading" className="mt-10">
      <div className="flex items-center justify-between pb-4">
        <div>
          <h2 id="your-projects-heading" className="text-xl font-semibold tracking-tight">
            Your projects
          </h2>
          <p className="text-xs text-muted-foreground">
            Resume working on your apps or create new versions.
          </p>
        </div>
        <Button asChild variant="ghost" size="sm">
          <Link href="/projects" className="gap-1 text-xs">
            View all ({projects.length})
            <ArrowRight className="size-3" />
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            onRename={setRenameProject}
            onArchive={handleArchive}
            onDelete={setDeleteProject}
          />
        ))}
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
    </section>
  );
}
