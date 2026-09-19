import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

/* Client-side validation limits mirror the server's own (app/api/auth/register/route.ts and the
 * control-plane): the client never accepts something the server would reject, and never rejects
 * something the server would accept. */
export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const NAME_MAX_LENGTH = 200;
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;

export function validateEmail(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) {
    return "Enter your email address.";
  }
  if (!EMAIL_PATTERN.test(trimmed)) {
    return "Enter a valid email address, like you@example.com.";
  }
  return undefined;
}

export function validateName(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) {
    return "Enter your name.";
  }
  if (trimmed.length > NAME_MAX_LENGTH) {
    return `Keep your name under ${NAME_MAX_LENGTH} characters.`;
  }
  return undefined;
}

export function validatePassword(
  value: string,
  options: { enforceLength: boolean },
): string | undefined {
  if (!value) {
    return "Enter your password.";
  }
  if (options.enforceLength && value.length < PASSWORD_MIN_LENGTH) {
    return `Use at least ${PASSWORD_MIN_LENGTH} characters.`;
  }
  if (options.enforceLength && value.length > PASSWORD_MAX_LENGTH) {
    return `Keep your password under ${PASSWORD_MAX_LENGTH} characters.`;
  }
  return undefined;
}

/** The control-plane's error strings are lower-case fragments ("invalid credentials"); shown
 * verbatim but sentence-cased and terminated, or the fallback when the body carried none. */
export function formatServerError(message: unknown, fallback: string): string {
  if (typeof message !== "string" || message.trim().length === 0) {
    return fallback;
  }
  const trimmed = message.trim();
  const sentence = trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  return /[.!?]$/.test(sentence) ? sentence : `${sentence}.`;
}

/** The id list an input should reference via `aria-describedby` for its hint and/or error. */
export function describedBy(id: string, error?: string, hint?: string): string | undefined {
  const ids = [error ? `${id}-error` : null, hint ? `${id}-hint` : null].filter(Boolean);
  return ids.length > 0 ? ids.join(" ") : undefined;
}

/** A labelled form field with an optional hint and an inline error. The control itself is
 * passed as children and wires `aria-invalid` + `aria-describedby` (see `describedBy`). */
export function Field({
  id,
  label,
  hint,
  error,
  children,
  className,
}: Readonly<{
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
  className?: string;
}>) {
  return (
    <div className={cn("grid gap-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="text-xs text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
