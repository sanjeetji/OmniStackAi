# The quality benchmark

`scripts/benchmark.sh` measures what the platform delivers for real prompts. It builds each one
exactly as the console does: the same planner, the same code generation and, with `--design`, the
same model-designed pages. It then runs the project and scores the result.

## When to run it

Run it after every change to planning, code generation or design, before calling that change done.
"Tasks completed" does not show whether apps got better; a higher benchmark score does.

The benchmark calls real models: the free tiers and local Ollama configured in `.env`. It is never
part of `task verify`.

## Running it

```bash
./scripts/omnistack.sh up                    # the database the previews use
scripts/benchmark.sh                         # the quick set: 8 varied prompts
scripts/benchmark.sh --design                # ... with pages designed by the model, as in the console
scripts/benchmark.sh --set full --design     # all 40 prompts (hours with free models)
scripts/benchmark.sh --only clinic,blog      # chosen cases
scripts/benchmark.sh --no-preview            # plans and code only
scripts/benchmark.sh --list                  # the prompts
scripts/benchmark.sh --rescore ~/.omnistackai/benchmark/<run>   # score a saved run again after the scoring changes
```

The benchmark type-checks the way the Studio does, with the cache `./scripts/omnistack.sh up` prepares
in `~/.omnistackai/web-typecheck`. Without that cache, every web app counts as not type-checked.

Results go to `~/.omnistackai/benchmark/<run>/`, or to `OMNISTACKAI_BENCHMARK_DIR` if set:

- `report.md` is for reading. It has a table of every case, then each case with its apps, what it
  stores, its building blocks, failing endpoints, UI problems and screenshots.
- `report.json` is for comparing runs.
- `<case>/repo` is the generated project, if you want to open it.
- `<case>/logs/ui-check/` holds every page's screenshot at phone and desktop width.

Each run is compared with the previous run in the same folder, or with `--baseline <report.json>`.
A case that falls by more than 10 points is listed as a **regression**, and the script then exits
with status 1.

## The score

Each case gets a score from 0 to 100. It is the weighted average of the parts that were measured:

| Part | Weight | What it measures |
|---|---|---|
| Build | 20 | The project was produced and every app type-checks: all clean or repaired is 100%, some not checked is 75% (a Python API that only parses counts as not checked), none checked is 50%, any failing is 25% |
| Runs | 20 | The preview started: the API and every web app came up |
| API | 15 | The share of list endpoints that answer 2xx against the real database |
| Pages | 15 | The share of page views, at phone and desktop width, with no overflow, console error, failed request, broken image or low contrast |
| Complete | 20 | What the prompt needs and the build has: the case's expected records, building blocks and number of apps |
| Designed | 10 | The share of pages the model designed rather than left as the template (only with `--design`) |

A part that was not measured is shown as a dash and left out of the average. It is not counted as
zero, and not counted as full marks either. A part goes unmeasured when there was no preview, no
design step, or no Chrome for the UI check.

The score does not yet include a judgement of how good the pages look. That arrives with the
design review (PC-130), which scores screenshots. Until then, look at the screenshots in
`report.md`.

## The prompts

They live in `services/agent-engine/src/omnistackai_agent_engine/benchmark/cases.py`.

- There are 40 cases: marketplaces and ecosystems, health, education, business software, consumer
  apps, bookings and organisations. Each is written the way people ask.
- Each case states the floor a reviewer would check first: the records it must store, the building
  blocks it needs (workflow, money, jobs, live updates, notifications, privacy), and how many apps.
- Do not edit a prompt to make a run pass. A case that changes gets a new id, so runs stay
  comparable.
