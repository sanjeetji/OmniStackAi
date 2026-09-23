"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { GitFork, LoaderCircle, Play } from "lucide-react";
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
import { cn } from "@/lib/utils";

/** "Use template": names the new project, creates the user's own copy, then opens it in Studio. */
export default function TemplateUseButton({
  slug,
  templateName,
  label = "Use template",
  variant = "default",
  size = "lg",
  autoCreate = false,
  className,
}: {
  slug: string;
  templateName: string;
  label?: string;
  variant?: "default" | "outline" | "secondary" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
  autoCreate?: boolean;
  className?: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(templateName);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function performCreate(projectName: string) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/templates/${encodeURIComponent(slug)}/use`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: projectName.trim() || templateName }),
      });
      const body = (await response.json().catch(() => ({}))) as { project?: { id: string }; error?: string };
      if (!response.ok || !body.project) {
        setError(body.error ?? "The project could not be created. Please try again.");
        setBusy(false);
        return;
      }
      router.push(`/studio/${encodeURIComponent(body.project.id)}`);
    } catch {
      setError("Couldn't reach the server. Please try again.");
      setBusy(false);
    }
  }

  function handleButtonClick() {
    if (autoCreate) {
      void performCreate(`${templateName} Live Demo`);
    } else {
      setOpen(true);
    }
  }

  return (
    <>
      <Button
        size={size}
        variant={variant}
        onClick={handleButtonClick}
        disabled={busy}
        className={cn("gap-1.5 shadow-xs font-semibold", className)}
      >
        {busy ? (
          <LoaderCircle className="animate-spin" aria-hidden="true" />
        ) : autoCreate ? (
          <Play className="fill-current size-4" aria-hidden="true" />
        ) : (
          <GitFork aria-hidden="true" />
        )}
        <span>{busy ? "Launching live apps…" : label}</span>
      </Button>

      {!autoCreate && (
        <Dialog open={open} onOpenChange={(next) => !busy && setOpen(next)}>
          <DialogContent className="sm:max-w-md">
            <form onSubmit={(e) => { e.preventDefault(); void performCreate(name); }}>
              <DialogHeader>
                <DialogTitle>Use {templateName}</DialogTitle>
                <DialogDescription>
                  This creates your own project with all of the template&rsquo;s apps, code and sample
                  data. You can change anything in it. The original template stays unchanged.
                </DialogDescription>
              </DialogHeader>
              <div className="mt-4 grid gap-1.5">
                <Label htmlFor="template-project-name">Project name</Label>
                <Input
                  id="template-project-name"
                  value={name}
                  maxLength={120}
                  onChange={(event) => setName(event.target.value)}
                  autoFocus
                />
              </div>
              {error ? (
                <p role="alert" className="mt-3 text-sm text-destructive">
                  {error}
                </p>
              ) : null}
              <DialogFooter className="mt-5">
                <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={busy}>
                  Cancel
                </Button>
                <Button type="submit" disabled={busy}>
                  {busy ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : null}
                  {busy ? "Creating your project…" : "Create project"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
