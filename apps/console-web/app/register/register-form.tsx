"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Field,
  NAME_MAX_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  describedBy,
  formatServerError,
  validateEmail,
  validateName,
  validatePassword,
} from "@/components/field";

interface Values {
  name: string;
  email: string;
  password: string;
}

type Errors = Partial<Record<keyof Values, string>>;

const PASSWORD_HINT = `At least ${PASSWORD_MIN_LENGTH} characters.`;

export default function RegisterForm() {
  const router = useRouter();
  const [values, setValues] = useState<Values>({ name: "", email: "", password: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  function update(field: keyof Values) {
    return (event: ChangeEvent<HTMLInputElement>) => {
      const next = event.target.value;
      setValues((current) => ({ ...current, [field]: next }));
      setErrors((current) => ({ ...current, [field]: undefined }));
    };
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors: Errors = {
      name: validateName(values.name),
      email: validateEmail(values.email),
      password: validatePassword(values.password, { enforceLength: true }),
    };
    if (nextErrors.name || nextErrors.email || nextErrors.password) {
      setErrors(nextErrors);
      return;
    }

    setServerError(null);
    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: values.email.trim(),
          name: values.name.trim(),
          password: values.password,
        }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { error?: unknown };
        setServerError(formatServerError(body.error, "Registration failed."));
        return;
      }
      router.push("/");
      router.refresh();
    } catch {
      setServerError("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate aria-busy={submitting} className="grid gap-4">
      {serverError ? (
        <div
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {serverError}
        </div>
      ) : null}

      <Field id="name" label="Name" error={errors.name}>
        <Input
          id="name"
          name="name"
          type="text"
          autoComplete="name"
          maxLength={NAME_MAX_LENGTH}
          autoFocus
          value={values.name}
          onChange={update("name")}
          aria-invalid={errors.name ? true : undefined}
          aria-describedby={describedBy("name", errors.name)}
        />
      </Field>

      <Field id="email" label="Email" error={errors.email}>
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          spellCheck={false}
          value={values.email}
          onChange={update("email")}
          aria-invalid={errors.email ? true : undefined}
          aria-describedby={describedBy("email", errors.email)}
        />
      </Field>

      <Field id="password" label="Password" hint={PASSWORD_HINT} error={errors.password}>
        <div className="relative">
          <Input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            maxLength={PASSWORD_MAX_LENGTH}
            value={values.password}
            onChange={update("password")}
            aria-invalid={errors.password ? true : undefined}
            aria-describedby={describedBy("password", errors.password, PASSWORD_HINT)}
            className="pr-9"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            className="absolute top-0.5 right-0.5 text-muted-foreground"
            aria-label={showPassword ? "Hide password" : "Show password"}
            aria-pressed={showPassword}
            onClick={() => setShowPassword((current) => !current)}
          >
            {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
          </Button>
        </div>
      </Field>

      <Button type="submit" size="lg" className="mt-2 w-full" disabled={submitting}>
        {submitting ? (
          <>
            <Loader2 className="animate-spin" aria-hidden="true" />
            Creating account…
          </>
        ) : (
          "Create account"
        )}
      </Button>
    </form>
  );
}
