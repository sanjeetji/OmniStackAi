"use client";

import { useEffect, useState } from "react";
import {
  Check,
  Copy,
  Crown,
  Edit2,
  ExternalLink,
  Loader2,
  Mail,
  MoreVertical,
  Plus,
  Shield,
  Trash2,
  UserMinus,
  UserPlus,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import type {
  Workspace,
  WorkspaceInvite,
  WorkspaceMember,
  WorkspaceRole,
} from "@/lib/control-plane";
import { formatRelativeTime } from "@/lib/time";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  getActiveWorkspaceId,
  setActiveWorkspaceId,
} from "./workspace-switcher";

export function WorkspaceManage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [invites, setInvites] = useState<WorkspaceInvite[]>([]);
  const [loading, setLoading] = useState(true);

  // Invite dialog
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<WorkspaceRole>("member");
  const [inviting, setInviting] = useState(false);
  const [lastInviteLink, setLastInviteLink] = useState<string | null>(null);

  // Edit workspace dialog
  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editSlug, setEditSlug] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  // Create workspace dialog
  const [createOpen, setCreateOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [creating, setCreating] = useState(false);

  const loadWorkspaces = async () => {
    try {
      const res = await fetch("/api/workspaces");
      if (!res.ok) return;
      const data = await res.json();
      const list: Workspace[] = data.workspaces || [];
      setWorkspaces(list);

      const activeId = getActiveWorkspaceId();
      const initial = list.find((w) => w.id === activeId) || list[0] || null;
      if (initial) {
        setSelectedWorkspace(initial);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const loadWorkspaceDetails = async (workspaceId: string) => {
    try {
      const [membersRes, invitesRes] = await Promise.all([
        fetch(`/api/workspaces/${workspaceId}/members`),
        fetch(`/api/workspaces/${workspaceId}/invites`),
      ]);

      if (membersRes.ok) {
        const memData = await membersRes.json();
        setMembers(memData.members || []);
      }
      if (invitesRes.ok) {
        const invData = await invitesRes.json();
        setInvites(invData.invites || []);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    let active = true;
    async function initWorkspaces() {
      try {
        const res = await fetch("/api/workspaces");
        if (!res.ok || !active) return;
        const data = await res.json();
        const list: Workspace[] = data.workspaces || [];
        if (!active) return;
        setWorkspaces(list);

        const activeId = getActiveWorkspaceId();
        const initial = list.find((w) => w.id === activeId) || list[0] || null;
        if (initial && active) {
          setSelectedWorkspace(initial);
        }
      } catch {
        // ignore
      } finally {
        if (active) setLoading(false);
      }
    }
    void initWorkspaces();
    return () => {
      active = false;
    };
  }, []);

  const selectedWorkspaceId = selectedWorkspace?.id;

  useEffect(() => {
    if (!selectedWorkspaceId) return;
    let active = true;
    async function loadDetails() {
      try {
        const [membersRes, invitesRes] = await Promise.all([
          fetch(`/api/workspaces/${selectedWorkspaceId}/members`),
          fetch(`/api/workspaces/${selectedWorkspaceId}/invites`),
        ]);

        if (membersRes.ok && active) {
          const memData = await membersRes.json();
          setMembers(memData.members || []);
        }
        if (invitesRes.ok && active) {
          const invData = await invitesRes.json();
          setInvites(invData.invites || []);
        }
      } catch {
        // ignore
      }
    }
    void loadDetails();
    return () => {
      active = false;
    };
  }, [selectedWorkspaceId]);

  const handleSelectWorkspace = (w: Workspace) => {
    setSelectedWorkspace(w);
    setActiveWorkspaceId(w.id);
  };

  const handleCreateWorkspace = async (e: React.FormEvent) => {
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
      setSelectedWorkspace(created);
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

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkspace || !editName.trim()) return;

    setSavingEdit(true);
    try {
      const res = await fetch(`/api/workspaces/${selectedWorkspace.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: editName.trim(), slug: editSlug.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to update workspace");
      }
      const updated: Workspace = await res.json();
      setWorkspaces((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));
      setSelectedWorkspace(updated);
      setEditOpen(false);
      toast.success("Workspace updated");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to update workspace");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkspace || !inviteEmail.trim()) return;

    setInviting(true);
    try {
      const res = await fetch(`/api/workspaces/${selectedWorkspace.id}/invites`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to send invitation");
      }
      const invite: WorkspaceInvite = await res.json();
      setInvites((prev) => [invite, ...prev]);
      const inviteUrl = `${window.location.origin}/invite/${invite.token}`;
      setLastInviteLink(inviteUrl);
      setInviteEmail("");
      toast.success(`Invitation sent to ${invite.email}`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to invite member");
    } finally {
      setInviting(false);
    }
  };

  const handleRevokeInvite = async (inviteId: string) => {
    if (!selectedWorkspace) return;
    try {
      const res = await fetch(`/api/workspaces/${selectedWorkspace.id}/invites/${inviteId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to revoke invite");
      setInvites((prev) => prev.filter((i) => i.id !== inviteId));
      toast.success("Invite revoked");
    } catch {
      toast.error("Could not revoke invite");
    }
  };

  const handleUpdateRole = async (userId: string, newRole: WorkspaceRole) => {
    if (!selectedWorkspace) return;
    try {
      const res = await fetch(`/api/workspaces/${selectedWorkspace.id}/members/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: newRole }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to update role");
      }
      const updated: WorkspaceMember = await res.json();
      setMembers((prev) => prev.map((m) => (m.user_id === userId ? updated : m)));
      toast.success("Role updated");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to update member role");
    }
  };

  const handleRemoveMember = async (userId: string, name: string) => {
    if (!selectedWorkspace) return;
    if (!confirm(`Are you sure you want to remove ${name} from ${selectedWorkspace.name}?`)) return;

    try {
      const res = await fetch(`/api/workspaces/${selectedWorkspace.id}/members/${userId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to remove member");
      }
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
      toast.success("Member removed");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to remove member");
    }
  };

  const handleDeleteWorkspace = async () => {
    if (!selectedWorkspace) return;
    if (
      !confirm(
        `Are you sure you want to delete workspace "${selectedWorkspace.name}"? All shared access will be removed.`
      )
    )
      return;

    try {
      const res = await fetch(`/api/workspaces/${selectedWorkspace.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to delete workspace");
      }
      toast.success("Workspace deleted");
      const remaining = workspaces.filter((w) => w.id !== selectedWorkspace.id);
      setWorkspaces(remaining);
      if (remaining.length > 0) {
        setSelectedWorkspace(remaining[0]);
        setActiveWorkspaceId(remaining[0].id);
      } else {
        setSelectedWorkspace(null);
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to delete workspace");
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12 text-sm text-muted-foreground">
          <Loader2 className="mr-2 size-4 animate-spin" />
          Loading workspace details…
        </CardContent>
      </Card>
    );
  }

  const isOwner = selectedWorkspace?.role === "owner";
  const isAdmin = isOwner || selectedWorkspace?.role === "admin";

  return (
    <div className="grid gap-6">
      {/* Workspace Selection & Header */}
      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-lg">Team & Workspaces</CardTitle>
            <CardDescription>
              Collaborate on projects, manage members, roles, and workspace invitations.
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCreateOpen(true)}
              className="gap-1.5"
            >
              <Plus className="size-3.5" />
              New workspace
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="flex flex-wrap items-center gap-2 border-b border-border/50 pb-4">
            <span className="text-xs font-medium text-muted-foreground mr-1">Workspace:</span>
            {workspaces.map((w) => {
              const active = selectedWorkspace?.id === w.id;
              return (
                <button
                  key={w.id}
                  type="button"
                  onClick={() => handleSelectWorkspace(w)}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    active
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                  }`}
                >
                  <Users className="size-3" />
                  <span>{w.name}</span>
                  {w.role && (
                    <span
                      className={`rounded px-1 text-[10px] uppercase font-mono ${
                        active ? "bg-primary-foreground/20 text-primary-foreground" : "bg-background/80"
                      }`}
                    >
                      {w.role}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {selectedWorkspace && (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pt-1">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold">{selectedWorkspace.name}</h3>
                  <Badge variant="outline" className="text-xs font-mono">
                    /{selectedWorkspace.slug}
                  </Badge>
                  {selectedWorkspace.role && (
                    <Badge variant="secondary" className="capitalize text-xs">
                      {selectedWorkspace.role}
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Created {formatRelativeTime(selectedWorkspace.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {isAdmin && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditName(selectedWorkspace.name);
                        setEditSlug(selectedWorkspace.slug);
                        setEditOpen(true);
                      }}
                      className="gap-1.5"
                    >
                      <Edit2 className="size-3.5" />
                      Settings
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => {
                        setLastInviteLink(null);
                        setInviteOpen(true);
                      }}
                      className="gap-1.5"
                    >
                      <UserPlus className="size-3.5" />
                      Invite member
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Members Section */}
      {selectedWorkspace && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base">Workspace Members</CardTitle>
              <CardDescription>
                People with access to projects inside {selectedWorkspace.name}.
              </CardDescription>
            </div>
            <Badge variant="secondary" className="text-xs">
              {members.length} {members.length === 1 ? "member" : "members"}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-border/40">
              {members.map((member) => (
                <div
                  key={member.user_id}
                  className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-xs uppercase">
                      {member.user_name ? member.user_name.slice(0, 2) : member.user_email.slice(0, 2)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-foreground">
                          {member.user_name || member.user_email}
                        </span>
                        {member.role === "owner" && (
                          <Crown className="size-3.5 text-amber-500" aria-label="Owner" />
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">{member.user_email}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-auto">
                    <span className="text-xs text-muted-foreground hidden md:inline">
                      Joined {formatRelativeTime(member.created_at)}
                    </span>

                    {isAdmin && member.role !== "owner" ? (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" size="sm" className="h-8 gap-1 text-xs capitalize">
                            <Shield className="size-3" />
                            {member.role}
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {(["admin", "member", "viewer"] as WorkspaceRole[]).map((r) => (
                            <DropdownMenuItem
                              key={r}
                              onClick={() => handleUpdateRole(member.user_id, r)}
                              className="capitalize text-xs"
                            >
                              {r}
                              {member.role === r && <Check className="ml-auto size-3.5" />}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    ) : (
                      <Badge variant="outline" className="capitalize text-xs">
                        {member.role}
                      </Badge>
                    )}

                    {isAdmin && member.role !== "owner" && (
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        onClick={() => handleRemoveMember(member.user_id, member.user_name || member.user_email)}
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        title="Remove member"
                      >
                        <UserMinus className="size-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pending Invites */}
      {selectedWorkspace && isAdmin && invites.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Pending Invitations</CardTitle>
            <CardDescription>
              Invited collaborators who haven&rsquo;t accepted yet.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-border/40">
              {invites.map((invite) => {
                const inviteUrl = `${typeof window !== "undefined" ? window.location.origin : ""}/invite/${invite.token}`;
                return (
                  <div
                    key={invite.id}
                    className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex size-8 items-center justify-center rounded-full bg-muted text-muted-foreground">
                        <Mail className="size-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground">
                            {invite.email}
                          </span>
                          <Badge variant="secondary" className="capitalize text-[10px]">
                            {invite.role}
                          </Badge>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          Invited {formatRelativeTime(invite.created_at)}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-auto">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 gap-1.5 text-xs"
                        onClick={() => {
                          navigator.clipboard.writeText(inviteUrl);
                          toast.success("Invite link copied to clipboard");
                        }}
                      >
                        <Copy className="size-3" />
                        Copy link
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => handleRevokeInvite(invite.id)}
                      >
                        Revoke
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Danger Zone */}
      {selectedWorkspace && isOwner && (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-base text-destructive">Danger Zone</CardTitle>
            <CardDescription>
              Permanently delete this workspace. Shared projects will remain accessible only to their original creators.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDeleteWorkspace}
              className="gap-1.5"
            >
              <Trash2 className="size-3.5" />
              Delete workspace
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Invite Member Dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleInvite}>
            <DialogHeader>
              <DialogTitle>Invite Member</DialogTitle>
              <DialogDescription>
                Invite a colleague or collaborator to join {selectedWorkspace?.name}.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="inv-email">Email address</Label>
                <Input
                  id="inv-email"
                  type="email"
                  placeholder="colleague@example.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  autoFocus
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="inv-role">Role</Label>
                <select
                  id="inv-role"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as WorkspaceRole)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="member">Member — Can create, edit, and build projects</option>
                  <option value="admin">Admin — Can invite members and manage workspace</option>
                  <option value="viewer">Viewer — Read-only access to projects and code</option>
                </select>
              </div>

              {lastInviteLink && (
                <div className="mt-2 rounded-lg border border-border/80 bg-muted/50 p-3">
                  <p className="text-xs font-medium text-foreground mb-1">
                    Invitation link created!
                  </p>
                  <div className="flex items-center gap-2">
                    <Input
                      readOnly
                      value={lastInviteLink}
                      className="font-mono text-xs h-8 select-all"
                    />
                    <Button
                      type="button"
                      size="sm"
                      className="h-8 shrink-0 gap-1 text-xs"
                      onClick={() => {
                        navigator.clipboard.writeText(lastInviteLink);
                        toast.success("Link copied!");
                      }}
                    >
                      <Copy className="size-3" />
                      Copy
                    </Button>
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setInviteOpen(false)}
                disabled={inviting}
              >
                Close
              </Button>
              <Button type="submit" disabled={inviting || !inviteEmail.trim()}>
                {inviting && <Loader2 className="mr-2 size-4 animate-spin" />}
                Send invite
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Workspace Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleSaveEdit}>
            <DialogHeader>
              <DialogTitle>Workspace Settings</DialogTitle>
              <DialogDescription>
                Update the name and URL identifier for this workspace.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-ws-name">Name</Label>
                <Input
                  id="edit-ws-name"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-ws-slug">Slug</Label>
                <Input
                  id="edit-ws-slug"
                  value={editSlug}
                  onChange={(e) => setEditSlug(e.target.value)}
                  required
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditOpen(false)}
                disabled={savingEdit}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={savingEdit || !editName.trim()}>
                {savingEdit && <Loader2 className="mr-2 size-4 animate-spin" />}
                Save changes
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Create Workspace Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleCreateWorkspace}>
            <DialogHeader>
              <DialogTitle>Create Workspace</DialogTitle>
              <DialogDescription>
                Create a team workspace for collaborative development.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="new-ws-name">Workspace name</Label>
                <Input
                  id="new-ws-name"
                  placeholder="e.g. Mobile Engineering"
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
    </div>
  );
}
