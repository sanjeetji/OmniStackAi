"use client";

import { useState, type FormEvent } from "react";
import type { Project } from "@/lib/control-plane";
import { Button } from "@/components/ui/button";
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

interface RenameDialogProps {
  project: Project | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRename: (projectId: string, newName: string, newDescription?: string) => Promise<void>;
}

export function RenameDialog({
  project,
  open,
  onOpenChange,
  onRename,
}: RenameDialogProps) {
  const [name, setName] = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync state when project changes
  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen && project) {
      setName(project.name);
      setDescription(project.description || "");
      setError(null);
    }
    onOpenChange(newOpen);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!project || !name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onRename(project.id, name.trim(), description.trim() || undefined);
      onOpenChange(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to rename project");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Rename Project</DialogTitle>
            <DialogDescription>
              Update the display name and description for this project.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="rename-name">Name</Label>
              <Input
                id="rename-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Project name"
                required
                disabled={saving}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="rename-desc">Description (optional)</Label>
              <Input
                id="rename-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description"
                disabled={saving}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving || !name.trim()}>
              {saving ? "Saving..." : "Save changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteDialogProps {
  project: Project | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDelete: (projectId: string, purge: boolean) => Promise<void>;
}

export function DeleteDialog({
  project,
  open,
  onOpenChange,
  onDelete,
}: DeleteDialogProps) {
  const [confirmName, setConfirmName] = useState("");
  const [purge, setPurge] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      setConfirmName("");
      setPurge(true);
      setError(null);
    }
    onOpenChange(newOpen);
  };

  const isConfirmed = project && confirmName.trim() === project.name.trim();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!project || !isConfirmed) return;
    setDeleting(true);
    setError(null);
    try {
      await onDelete(project.id, purge);
      onOpenChange(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete project");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="text-destructive">Delete Project</DialogTitle>
            <DialogDescription>
              This action cannot be undone. To confirm deletion, type the project name{" "}
              <strong className="text-foreground">{project?.name}</strong> below.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="delete-confirm">Confirm project name</Label>
              <Input
                id="delete-confirm"
                value={confirmName}
                onChange={(e) => setConfirmName(e.target.value)}
                placeholder={project?.name}
                autoFocus
                disabled={deleting}
              />
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="delete-purge"
                checked={purge}
                onChange={(e) => setPurge(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                disabled={deleting}
              />
              <Label htmlFor="delete-purge" className="text-xs text-muted-foreground">
                Also purge the on-disk workspace repository files
              </Label>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="destructive"
              disabled={deleting || !isConfirmed}
            >
              {deleting ? "Deleting..." : "Delete project"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
