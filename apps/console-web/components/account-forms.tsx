"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { CircleCheck, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  describedBy,
  formatServerError,
  validateEmail,
  validatePassword,
} from "@/components/field";

/** PC-012: the signed-out account flows - confirm an email address, ask for a reset link, and
 * choose a new password. Every decision is the control plane's; these only carry the request. */

async function post(path: string, body: unknown): Promise<{ ok: boolean; data: Record<string, unknown> }> {
  const response = await fetch(`/api/account/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  return { ok: response.ok, data };
}

function Alert({ tone, children }: Readonly<{ tone: "error" | "ok"; children: React.ReactNode }>) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={
        tone === "error"
          ? "rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          : "flex items-start gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm"
      }
    >
      {tone === "ok" ? <CircleCheck className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden="true" /> : null}
      <span>{children}</span>
    </div>
  );
}

const LINK = "font-medium text-foreground underline underline-offset-4 hover:text-brand";

export function VerifyEmail({ token }: Readonly<{ token: string }>) {
  const [state, setState] = useState<{ status: "working" | "done" | "failed"; message?: string }>({
    status: token ? "working" : "failed",
    message: token ? undefined : "This link is incomplete. Send a new one from Settings.",
  });
  const sent = useRef(false);

  useEffect(() => {
    if (!token || sent.current) return;
    sent.current = true;
    post("verify-email", { token })
      .then(({ ok, data }) =>
        setState(
          ok
            ? { status: "done" }
            : { status: "failed", message: formatServerError(data.error, "This link did not work.") },
        ),
      )
      .catch(() => setState({ status: "failed", message: "Couldn't reach the server. Try the link again." }));
  }, [token]);

  if (state.status === "working") {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <Loader2 className="size-4 animate-spin" aria-hidden="true" /> Confirming your email…
      </p>
    );
  }
  if (state.status === "done") {
    return (
      <div className="grid gap-4">
        <Alert tone="ok">Your email is confirmed. You can build and publish now.</Alert>
        <Button asChild size="lg" className="w-full">
          <Link href="/">Go to your projects</Link>
        </Button>
      </div>
    );
  }
  return (
    <div className="grid gap-4">
      <Alert tone="error">{state.message}</Alert>
      <Link href="/settings#account" className={LINK}>
        Open Settings
      </Link>
    </div>
  );
}

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [done, setDone] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const invalid = validateEmail(email);
    if (invalid) {
      setError(invalid);
      return;
    }
    setSubmitting(true);
    setError(undefined);
    try {
      const { ok, data } = await post("forgot-password", { email: email.trim() });
      if (!ok) {
        setError(formatServerError(data.error, "That did not work. Try again."));
        return;
      }
      setDone(
        typeof data.status === "string"
          ? data.status
          : "If an account uses that address, a link to choose a new password is on its way.",
      );
    } catch {
      setError("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) return <Alert tone="ok">{done}</Alert>;
  return (
    <form onSubmit={submit} noValidate aria-busy={submitting} className="grid gap-4">
      <Field id="email" label="Email" error={error}>
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          spellCheck={false}
          autoFocus
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            setError(undefined);
          }}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy("email", error)}
        />
      </Field>
      <Button type="submit" size="lg" className="w-full" disabled={submitting}>
        {submitting ? <Loader2 className="animate-spin" aria-hidden="true" /> : null}
        Send the link
      </Button>
    </form>
  );
}

const PASSWORD_HINT = `At least ${PASSWORD_MIN_LENGTH} characters.`;

export function ResetPasswordForm({ token }: Readonly<{ token: string }>) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [serverError, setServerError] = useState<string | null>(
    token ? null : "This link is incomplete. Ask for a new one.",
  );
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const invalid = validatePassword(password, { enforceLength: true });
    if (invalid) {
      setError(invalid);
      return;
    }
    setSubmitting(true);
    setServerError(null);
    try {
      const { ok, data } = await post("reset-password", { token, new_password: password });
      if (!ok) {
        setServerError(formatServerError(data.error, "That did not work. Ask for a new link."));
        return;
      }
      setDone(true);
    } catch {
      setServerError("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="grid gap-4">
        <Alert tone="ok">Your password is changed and every device was signed out. Sign in with the new one.</Alert>
        <Button asChild size="lg" className="w-full">
          <Link href="/login">Sign in</Link>
        </Button>
      </div>
    );
  }
  return (
    <form onSubmit={submit} noValidate aria-busy={submitting} className="grid gap-4">
      {serverError ? <Alert tone="error">{serverError}</Alert> : null}
      <Field id="password" label="New password" hint={PASSWORD_HINT} error={error}>
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          maxLength={PASSWORD_MAX_LENGTH}
          autoFocus
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
            setError(undefined);
          }}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy("password", error, PASSWORD_HINT)}
        />
      </Field>
      <Button type="submit" size="lg" className="w-full" disabled={submitting || !token}>
        {submitting ? <Loader2 className="animate-spin" aria-hidden="true" /> : null}
        Set the new password
      </Button>
    </form>
  );
}
