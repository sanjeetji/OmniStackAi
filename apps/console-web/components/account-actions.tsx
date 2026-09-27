"use client";

import { useState, type FormEvent } from "react";
import { Download, Loader2, MailCheck, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatServerError } from "@/components/field";

/** PC-012: Settings → Account. Email confirmation status (with "send the link again"), a download
 * of everything tied to the account, and deleting the account behind its password. */
export function AccountActions({ email, verified }: Readonly<{ email: string; verified: boolean }>) {
  return (
    <div className="mt-6 grid gap-4 border-t border-border pt-5">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-muted-foreground">Email</span>
        {verified ? (
          <Badge variant="secondary">Confirmed</Badge>
        ) : (
          <>
            <Badge variant="outline">Not confirmed</Badge>
            <ResendButton email={email} />
          </>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button asChild variant="outline" size="sm">
          <a href="/api/account/me/export" download>
            <Download aria-hidden="true" /> Download my data
          </a>
        </Button>
        <DeleteAccount />
      </div>
    </div>
  );
}

export function ResendButton({ email, size = "sm" }: Readonly<{ email: string; size?: "sm" | "xs" }>) {
  const [sending, setSending] = useState(false);
  async function resend() {
    setSending(true);
    try {
      const response = await fetch("/api/account/verify-email/resend", { method: "POST" });
      const body = (await response.json().catch(() => ({}))) as { error?: unknown };
      if (response.ok) toast.success(`A new link is on its way to ${email}.`);
      else toast.error(formatServerError(body.error, "The link could not be sent."));
    } catch {
      toast.error("Couldn't reach the server.");
    } finally {
      setSending(false);
    }
  }
  return (
    <Button variant="outline" size={size} onClick={resend} disabled={sending}>
      {sending ? <Loader2 className="animate-spin" aria-hidden="true" /> : <MailCheck aria-hidden="true" />}
      Send the link again
    </Button>
  );
}

function DeleteAccount() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDeleting(true);
    setError(null);
    try {
      const response = await fetch("/api/account/me/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const body = (await response.json().catch(() => ({}))) as { error?: unknown };
      if (!response.ok) {
        setError(formatServerError(body.error, "The account could not be deleted."));
        return;
      }
      window.location.href = "/login";
    } catch {
      setError("Couldn't reach the server. Nothing was deleted.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="text-destructive hover:text-destructive">
          <Trash2 aria-hidden="true" /> Delete account
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle>Delete your account?</DialogTitle>
            <DialogDescription>
              Your projects, previews, published apps, keys and history are removed, and a paid plan is
              cancelled. This cannot be undone. Download your data first if you want a copy.
            </DialogDescription>
          </DialogHeader>
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
          <div className="grid gap-1.5">
            <Label htmlFor="delete-password">Your password</Label>
            <Input
              id="delete-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <DialogFooter>
            <Button type="submit" variant="destructive" disabled={deleting || password.length === 0}>
              {deleting ? <Loader2 className="animate-spin" aria-hidden="true" /> : null}
              Delete everything
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
