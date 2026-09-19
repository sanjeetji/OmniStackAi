"use client";

import { useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUp, LoaderCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/* The same real, runnable prompts the Studio's empty state offers (studio-chat.tsx), with short
 * chip labels for the home page. Clicking a chip fills the composer; nothing is sent until the
 * person presses Build. */
export const HOME_EXAMPLES = [
  {
    label: "Task tracker",
    prompt: "A task tracker where users create projects and each project has tasks with due dates",
  },
  { label: "Recipe box", prompt: "A recipe box with tags, ratings and a weekly meal plan" },
  { label: "Simple CRM", prompt: "A simple CRM: companies, contacts and notes, with a search page" },
];

/** Prompt-first home (R-497, after Dyad's and Lovable's home screens): a real composer that
 * hands the prompt to the Studio via `/studio?prompt=…`, where the build starts through the
 * Studio's own submit path. */
export default function HomeComposer({ className }: { className?: string }) {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [navigating, setNavigating] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || navigating) return;
    setNavigating(true);
    router.push(`/studio?prompt=${encodeURIComponent(trimmed)}`);
  }

  return (
    <form onSubmit={handleSubmit} className={cn("grid gap-3", className)}>
      <div className="flex items-end gap-2 rounded-2xl border border-input bg-card p-2 shadow-sm transition-[color,box-shadow] focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
        <textarea
          ref={textareaRef}
          aria-label="Describe the app to build"
          placeholder="A task tracker where users create projects and each project has tasks…"
          rows={2}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          disabled={navigating}
          className="field-sizing-content max-h-48 min-h-14 flex-1 resize-none bg-transparent px-2 py-1.5 text-base outline-none placeholder:text-muted-foreground disabled:opacity-60 md:text-sm"
        />
        <Button
          type="submit"
          size="icon"
          aria-label="Build"
          disabled={navigating || prompt.trim().length === 0}
        >
          {navigating ? (
            <LoaderCircle className="animate-spin" aria-hidden="true" />
          ) : (
            <ArrowUp aria-hidden="true" />
          )}
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {HOME_EXAMPLES.map(({ label, prompt: example }) => (
          <button
            key={label}
            type="button"
            onClick={() => {
              setPrompt(example);
              textareaRef.current?.focus();
            }}
            className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-background px-3 py-1.5 text-xs text-muted-foreground outline-none transition-colors select-none hover:border-brand/40 hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 active:translate-y-px"
          >
            <Sparkles className="size-3 text-brand" aria-hidden="true" />
            {label}
          </button>
        ))}
        <Link
          href="/studio"
          className="ml-auto text-xs text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
        >
          Open the Studio →
        </Link>
      </div>
    </form>
  );
}
