"use client";

import { useEffect, useId, useMemo, useState, type FormEvent } from "react";
import {
  Check,
  CheckCircle2,
  Copy,
  Edit2,
  Eye,
  LoaderCircle,
  Plus,
  Sparkles,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import type { Skill } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
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

const KEBAB_REGEX = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const MAX_BODY_CHARS = 8192;

interface StarterTemplate {
  name: string;
  title: string;
  description: string;
  body: string;
}

const STARTER_TEMPLATES: StarterTemplate[] = [
  {
    name: "design-system",
    title: "Design System & UI Guidelines",
    description: "UI conventions, styling, color palette, and component design patterns.",
    body: `- Use Tailwind CSS with clean, modern utility classes and semantic tokens.
- Follow a sleek, cohesive color palette with subtle borders, muted backgrounds, and dark-mode first contrast.
- Prefer rounded-xl corners, smooth transitions, and accessible focus rings.
- Ensure all interactive elements have hover and active states.`,
  },
  {
    name: "coding-standards",
    title: "Coding Standards & Quality",
    description: "Strict TypeScript conventions, functional components, and error handling.",
    body: `- Use TypeScript strict mode. Never use 'any'; prefer explicit types and interfaces.
- Write functional, modular components with single responsibility.
- Handle all loading, empty, and error states gracefully in the UI.
- Keep dependencies minimal and prefer standard web APIs where possible.`,
  },
  {
    name: "domain-rules",
    title: "Domain Rules & Business Logic",
    description: "Core domain models, validation, and business workflow constraints.",
    body: `- Ensure all business calculations (pricing, totals, taxes) are accurate and validated.
- Format dates, currencies, and numbers using standard locale-aware utilities.
- Enforce idempotency on state mutations and form submissions.`,
  },
  {
    name: "copy-and-tone",
    title: "Copy & Tone Guidelines",
    description: "User-facing microcopy, tone of voice, and error messaging.",
    body: `- Maintain a friendly, concise, and helpful tone throughout the user interface.
- Use sentence case for headings, buttons, and labels.
- Provide actionable, clear error messages explaining how the user can resolve the issue.`,
  },
];

export function SkillsLibrary({
  className,
  onSkillsChange,
}: {
  className?: string;
  onSkillsChange?: () => void;
}) {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Editor Dialog state
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);

  // Delete Dialog state
  const [deleteConfirmSkill, setDeleteConfirmSkill] = useState<Skill | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchSkills = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/skills");
      if (!res.ok) {
        throw new Error("Failed to load skills library");
      }
      const data = await res.json();
      setSkills(data.skills ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load skills");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetch("/api/skills");
        if (!res.ok) {
          throw new Error("Failed to load skills library");
        }
        const data = await res.json();
        if (active) setSkills(data.skills ?? []);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Failed to load skills");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const handleOpenNew = () => {
    setEditingSkill(null);
    setEditorOpen(true);
  };

  const handleOpenEdit = (skill: Skill) => {
    setEditingSkill(skill);
    setEditorOpen(true);
  };

  const handleDelete = async (skill: Skill) => {
    setDeleting(true);
    try {
      const res = await fetch(`/api/skills/${encodeURIComponent(skill.id)}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Failed to delete skill");
      }
      setDeleteConfirmSkill(null);
      await fetchSkills();
      onSkillsChange?.();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete skill");
    } finally {
      setDeleting(false);
    }
  };

  const handleEditorSaved = () => {
    setEditorOpen(false);
    setEditingSkill(null);
    fetchSkills();
    onSkillsChange?.();
  };

  return (
    <div className={cn("grid gap-4", className)}>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle id="skills-title" className="text-lg flex items-center gap-2">
                <Sparkles className="size-4 text-brand" />
                Skills Library
              </CardTitle>
              <CardDescription>
                Reusable instruction sets attached to projects, set as defaults, or invoked with @mentions.
              </CardDescription>
            </div>
            <Button size="sm" onClick={handleOpenNew} className="gap-1.5">
              <Plus className="size-3.5" />
              New skill
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div
              role="alert"
              className="mb-4 flex gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <LoaderCircle className="size-5 animate-spin mr-2" />
              Loading skills...
            </div>
          ) : skills.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/80 p-8 text-center">
              <Sparkles className="mx-auto size-8 text-muted-foreground/60" />
              <h3 className="mt-2 text-sm font-semibold">No skills created yet</h3>
              <p className="mt-1 text-xs text-muted-foreground max-w-sm mx-auto">
                Create custom instruction sets like design systems, coding standards, or domain rules to guide your builds.
              </p>
              <Button size="sm" variant="outline" onClick={handleOpenNew} className="mt-4 gap-1.5">
                <Plus className="size-3.5" />
                Create your first skill
              </Button>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {skills.map((skill) => (
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
                    <span>{skill.body.length.toLocaleString()} / {MAX_BODY_CHARS.toLocaleString()} chars</span>
                    <div className="flex items-center gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="size-7"
                        title="Edit skill"
                        onClick={() => handleOpenEdit(skill)}
                      >
                        <Edit2 className="size-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="size-7 text-destructive hover:text-destructive"
                        title="Delete skill"
                        onClick={() => setDeleteConfirmSkill(skill)}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Skill Editor Dialog */}
      <SkillEditorDialog
        open={editorOpen}
        onOpenChange={setEditorOpen}
        skill={editingSkill}
        onSaved={handleEditorSaved}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmSkill !== null}
        onOpenChange={(open) => !open && setDeleteConfirmSkill(null)}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Skill</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <span className="font-semibold text-foreground">{deleteConfirmSkill?.title}</span> (<code>@{deleteConfirmSkill?.name}</code>)? This will also detach it from any projects using it.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              disabled={deleting}
              onClick={() => setDeleteConfirmSkill(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={deleting}
              onClick={() => deleteConfirmSkill && handleDelete(deleteConfirmSkill)}
            >
              {deleting ? (
                <>
                  <LoaderCircle className="size-3.5 animate-spin mr-1.5" />
                  Deleting...
                </>
              ) : (
                "Delete skill"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function SkillEditorDialog({
  open,
  onOpenChange,
  skill,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  skill: Skill | null;
  onSaved: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        {open && (
          <SkillEditorForm
            key={skill ? skill.id : "new"}
            skill={skill}
            onCancel={() => onOpenChange(false)}
            onSaved={onSaved}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function SkillEditorForm({
  skill,
  onCancel,
  onSaved,
}: {
  skill: Skill | null;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const isEditing = skill !== null;
  const [name, setName] = useState(skill?.name ?? "");
  const [title, setTitle] = useState(skill?.title ?? "");
  const [description, setDescription] = useState(skill?.description ?? "");
  const [body, setBody] = useState(skill?.body ?? "");
  const [isDefault, setIsDefault] = useState(skill?.is_default ?? false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const defaultId = useId();

  // Validation
  const isNameValid = useMemo(() => {
    if (isEditing) return true; // Name is immutable on update
    return KEBAB_REGEX.test(name) && name.length <= 64;
  }, [name, isEditing]);

  const isBodyValid = body.trim().length > 0 && body.length <= MAX_BODY_CHARS;
  const canSave = (isEditing || isNameValid) && title.trim().length > 0 && isBodyValid;

  const applyTemplate = (tpl: StarterTemplate) => {
    if (!isEditing) {
      setName(tpl.name);
    }
    setTitle(tpl.title);
    setDescription(tpl.description);
    setBody(tpl.body);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSave) return;

    setSaving(true);
    setError(null);

    try {
      if (isEditing) {
        const res = await fetch(`/api/skills/${encodeURIComponent(skill.id)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: title.trim(),
            description: description.trim(),
            body: body.trim(),
            is_default: isDefault,
          }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.error || "Failed to update skill");
        }
      } else {
        const res = await fetch("/api/skills", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: name.trim().toLowerCase(),
            title: title.trim(),
            description: description.trim(),
            body: body.trim(),
            is_default: isDefault,
          }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.error || "Failed to create skill");
        }
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save skill");
    } finally {
      setSaving(false);
    }
  };

  const previewMarkdown = useMemo(() => {
    const skillName = name.trim().toLowerCase() || "skill-name";
    const skillBody = body.trim() || "(Skill instructions will appear here)";
    return `### ${skillName}\n${skillBody}`;
  }, [name, body]);

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>{isEditing ? "Edit Skill" : "New Skill"}</DialogTitle>
            <DialogDescription>
              {isEditing
                ? "Update your custom instruction set. The identifier @name cannot be changed."
                : "Create a reusable instruction set for code generation and editing."}
            </DialogDescription>
          </DialogHeader>

          {/* One-click starter templates */}
          {!isEditing && (
            <div className="rounded-lg border border-border/60 bg-muted/30 p-3 space-y-2">
              <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                <Sparkles className="size-3.5 text-brand" />
                Starter templates:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {STARTER_TEMPLATES.map((tpl) => (
                  <button
                    key={tpl.name}
                    type="button"
                    onClick={() => applyTemplate(tpl)}
                    className="rounded-md border border-border/80 bg-background px-2.5 py-1 text-xs text-muted-foreground hover:border-brand/40 hover:text-foreground transition-colors"
                  >
                    {tpl.title.split("&")[0].trim()}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="grid gap-1.5">
              <Label htmlFor="skill-name">
                Identifier <span className="text-muted-foreground font-normal">(@name)</span>
              </Label>
              <Input
                id="skill-name"
                value={name}
                onChange={(e) => setName(e.target.value.toLowerCase())}
                placeholder="e.g. design-system"
                disabled={isEditing || saving}
                required
                className={cn(
                  !isEditing && name.length > 0 && !isNameValid && "border-destructive focus-visible:ring-destructive/30"
                )}
              />
              {!isEditing && name.length > 0 && !isNameValid && (
                <p className="text-[11px] text-destructive">
                  Must be lower-kebab-case (e.g. <code>design-system</code>, max 64 chars).
                </p>
              )}
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="skill-title">Display Title</Label>
              <Input
                id="skill-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Design System & UI"
                disabled={saving}
                required
              />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="skill-desc">Description (optional)</Label>
            <Input
              id="skill-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief summary of when and how this skill applies"
              disabled={saving}
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id={defaultId}
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              disabled={saving}
              className="size-4 rounded border-border text-brand focus:ring-brand/30"
            />
            <Label htmlFor={defaultId} className="text-xs font-normal cursor-pointer">
              Apply by default to all projects in your account
            </Label>
          </div>

          <div className="grid gap-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="skill-body">Instructions (Body)</Label>
              <span
                className={cn(
                  "text-xs tabular-nums",
                  body.length > MAX_BODY_CHARS ? "text-destructive font-semibold" : "text-muted-foreground"
                )}
              >
                {body.length.toLocaleString()} / {MAX_BODY_CHARS.toLocaleString()}
              </span>
            </div>
            <textarea
              id="skill-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Enter instructions, constraints, or guidelines for the model..."
              disabled={saving}
              rows={6}
              className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
              required
            />
          </div>

          {/* Live Preview Pane */}
          <div className="rounded-lg border border-border/60 bg-muted/20 p-3 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Eye className="size-3.5" />
              What the model will see:
            </div>
            <pre className="rounded bg-background p-2.5 font-mono text-xs text-foreground/90 overflow-x-auto whitespace-pre-wrap border border-border/40">
              {previewMarkdown}
            </pre>
          </div>

          {error && (
            <p className="text-xs text-destructive flex items-center gap-1.5">
              <TriangleAlert className="size-3.5 shrink-0" />
              {error}
            </p>
          )}

          <DialogFooter className="gap-2 sm:gap-0 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!canSave || saving}>
              {saving ? (
                <>
                  <LoaderCircle className="size-3.5 animate-spin mr-1.5" />
                  Saving...
                </>
              ) : isEditing ? (
                "Save changes"
              ) : (
                "Create skill"
              )}
            </Button>
          </DialogFooter>
        </form>
  );
}
