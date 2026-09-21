"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Check, ChevronDown, Loader2, Plus, Settings, Users } from "lucide-react";
import { toast } from "sonner";
import type { Workspace } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const ACTIVE_WORKSPACE_STORAGE_KEY = "omnistack_active_workspace_id";

export function getActiveWorkspaceId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
}

export function setActiveWorkspaceId(id: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, id);
  window.dispatchEvent(new CustomEvent("workspace-changed", { detail: { workspaceId: id } }));
}

export default function WorkspaceSwitcher() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    let active = true;
    async function loadWorkspaces() {
      try {
        const res = await fetch("/api/workspaces");
        if (!res.ok || !active) return;
        const data = await res.json();
        const list: Workspace[] = data.workspaces || [];
        if (!active) return;
        setWorkspaces(list);

        const savedId = getActiveWorkspaceId();
        const found = list.find((w) => w.id === savedId) || list[0] || null;
        if (found && active) {
          setActiveWorkspace(found);
          if (savedId !== found.id) {
            setActiveWorkspaceId(found.id);
          }
        }
      } catch {
        // ignore
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadWorkspaces();

    const handleStorage = (e: StorageEvent) => {
      if (e.key === ACTIVE_WORKSPACE_STORAGE_KEY && e.newValue) {
        setWorkspaces((prev) => {
          const match = prev.find((w) => w.id === e.newValue);
          if (match) setActiveWorkspace(match);
          return prev;
        });
      }
    };

    const handleCustomChange = (e: Event) => {
      const customEvent = e as CustomEvent<{ workspaceId: string }>;
      if (customEvent.detail?.workspaceId) {
        setWorkspaces((prev) => {
          const match = prev.find((w) => w.id === customEvent.detail.workspaceId);
          if (match) setActiveWorkspace(match);
          return prev;
        });
      }
    };

    window.addEventListener("storage", handleStorage);
    window.addEventListener("workspace-changed", handleCustomChange);
    return () => {
      active = false;
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("workspace-changed", handleCustomChange);
    };
  }, []);

  const handleSelect = (workspace: Workspace) => {
    setActiveWorkspace(workspace);
    setActiveWorkspaceId(workspace.id);
    toast.success(`Switched to ${workspace.name}`);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim()) return;

    setCreating(true);
    try {
      const res = await fetch("/api/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newWorkspaceName.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to create workspace");
      }
      const created: Workspace = await res.json();
      setWorkspaces((prev) => [created, ...prev]);
      setActiveWorkspace(created);
      setActiveWorkspaceId(created.id);
      setNewWorkspaceName("");
      setCreateOpen(false);
      toast.success(`Workspace "${created.name}" created`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to create workspace");
    } finally {
      setCreating(false);
    }
  };

  if (loading && !activeWorkspace) {
    return (
      <div className="flex h-8 items-center gap-1.5 rounded-lg border border-border/40 px-2.5 text-xs text-muted-foreground">
        <Loader2 className="size-3.5 animate-spin" />
        <span>Loading workspace…</span>
      </div>
    );
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            aria-label="Workspace switcher"
            className="group inline-flex h-8 items-center gap-2 rounded-lg border border-border/50 bg-background/50 px-2.5 text-xs outline-none transition-all hover:bg-muted/60 hover:border-border focus-visible:ring-3 focus-visible:ring-ring/50 aria-expanded:bg-muted active:translate-y-px"
          >
            <div className="flex size-4 items-center justify-center rounded bg-primary/10 text-primary">
              <Users className="size-2.5" />
            </div>
            <span className="max-w-[130px] truncate font-medium text-foreground sm:max-w-[180px]">
              {activeWorkspace ? activeWorkspace.name : "Select workspace"}
            </span>
            {activeWorkspace?.role && (
              <Badge variant="outline" className="hidden text-[10px] uppercase font-mono px-1 py-0 sm:inline-flex">
                {activeWorkspace.role}
              </Badge>
            )}
            <ChevronDown
              aria-hidden="true"
              className="size-3 text-muted-foreground transition-transform group-aria-expanded:rotate-180"
            />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel className="text-xs text-muted-foreground">
            Workspaces
          </DropdownMenuLabel>
          <DropdownMenuGroup>
            {workspaces.map((w) => {
              const isSelected = activeWorkspace?.id === w.id;
              return (
                <DropdownMenuItem
                  key={w.id}
                  onClick={() => handleSelect(w)}
                  className="flex items-center justify-between gap-2 text-sm"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="truncate">{w.name}</span>
                    {w.role && (
                      <Badge variant="secondary" className="text-[10px] px-1 py-0">
                        {w.role}
                      </Badge>
                    )}
                  </div>
                  {isSelected && <Check className="size-4 text-primary shrink-0" />}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={() => setCreateOpen(true)}
            className="cursor-pointer text-sm"
          >
            <Plus className="mr-2 size-4" />
            <span>Create workspace</span>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/settings#team" className="cursor-pointer text-sm">
              <Settings className="mr-2 size-4" />
              <span>Manage team & workspaces</span>
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleCreate}>
            <DialogHeader>
              <DialogTitle>Create Workspace</DialogTitle>
              <DialogDescription>
                Create a collaborative space to build apps and invite team members.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="ws-name">Workspace name</Label>
                <Input
                  id="ws-name"
                  placeholder="e.g. Acme Engineering"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  autoFocus
                  required
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateOpen(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={creating || !newWorkspaceName.trim()}>
                {creating && <Loader2 className="mr-2 size-4 animate-spin" />}
                Create
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
