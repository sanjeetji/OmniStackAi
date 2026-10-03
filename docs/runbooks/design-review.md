# The design review

A page can pass every code check and still look poor: crowded, unbalanced, a badge on top of a
button. Only looking at it shows that. So after the model designs a project's pages, the Studio looks
at them.

1. **Screenshot.** Every page is screenshotted again at desktop and phone width, as it is now.
   This needs the preview running; the preview's own check ran before the pages were designed.
2. **Score.** A model that can see is shown both screenshots of each page. It scores the page from
   1 to 10 against a fixed rubric and lists the most visible problems, each with its fix. The rubric
   covers hierarchy, spacing and alignment, overlap and clipping, readability, consistency, empty
   states, the phone layout, and whether the page looks like a finished modern product.
3. **Improve.** Every page below the bar (7 by default) is designed again, with its review as the
   brief. The new page goes through the usual checks (types, links, colours) or is put back.

The chat reports the average score and how many pages were redesigned. The full review, with every
page's score and problems, is kept in the project's `logs/design-review/review.json`.

## Which model looks

The order is Anthropic, OpenAI, then Gemini, when their keys are set. After them come OpenRouter's
free vision models (`qwen/qwen3.8-27b:free`, `google/gemma-4-31b-it:free`), which keep the review
working once Gemini's free daily quota is spent. `OMNISTACKAI_VISION_CHAIN` (`provider:model`,
comma-separated) replaces the list. With no model that can see, the review says so and changes
nothing.

`OMNISTACKAI_DESIGN_REVIEW_PASS` sets the bar (default 7).

## In the benchmark

`scripts/benchmark.sh --review` adds a **Looks** score to every case: the review's average out of 10.
The report shows the worst pages and why.

## Limits

- Phone screens are reviewed on the emulator by hand for now. The review covers the web and admin
  apps, which the browser check screenshots.
- One round per run. Running the review again re-scores the pages and improves what is still below
  the bar.
