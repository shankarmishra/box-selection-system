# AI Usage

## Tool used

**Claude Code** (Anthropic's agentic CLI, running Opus 5), used in its
**agentic mode** — not copy-pasting snippets from a chat window into an
editor. I gave it the assignment brief and my goals, it read the assignment
docx itself, asked me clarifying questions up front, wrote a plan, and then
built the project end-to-end in one continuous session: writing files,
running `pytest`/`ruff`/`django manage.py` commands itself, reading the real
output, and fixing what it found broken — the same loop I'd run manually,
just executed by the tool with me reviewing checkpoints along the way.

That's a meaningfully different usage pattern from "ask ChatGPT for a
function, paste it in," so I'm calling it out explicitly rather than letting
the prompt log below imply a normal chat transcript.

## Ground rules I set before it started building

Given up front, before any code was written:

1. **No third-party bin-packing library.** The packing algorithm *is* the
   assignment — pulling in `py3dbp` or similar would technically produce
   working code while skipping the part actually being evaluated.
2. **Real Python must be installed and everything actually run**, not
   claimed to work. Every test result, lint pass, and demo output in this
   repo is real output I watched the tool produce, not generated prose.
3. **`AI_USAGE.md` gets logged factually as the build happens**, including
   real mistakes — not written retrospectively as marketing copy.
4. **I write `LEARNINGS.md` and the transcript export myself.** The
   assignment explicitly disqualifies AI-written answers for those two
   items, so the tool was told not to touch them beyond leaving a stub.

## What I asked for

My original request (paraphrased from Hinglish): *check the assignment docx
properly, build the project so I can explain any of it easily in an
interview, and make the AI-usage documentation genuinely interesting/
different from what other candidates will submit — put it all in one folder
on the Desktop and start.*

The tool's response before writing any code was to actually open and parse
the `.docx`, then ask me three clarifying questions rather than guess:

| Question | What I chose | Why it mattered |
|---|---|---|
| No real Python was installed (only the Windows Store stub) — install properly, or work around it? | Install properly via `winget` | Needed for every test run in this repo to be real, not simulated |
| How ambitious should the build be, given "easy to explain" and "stands out" pull in opposite directions? | Full build | I wanted the explainability trace + visualizer, not just the minimum |
| Public or private GitHub repo? | Public | Assignment needs a repo link + Actions run a reviewer can open without an invite |

## What I accepted as-is

- The overall architecture (`packing/` pure domain, `warehouse/` ORM +
  adapter, `api/` DRF + views) — matches how I'd have split it myself, and
  the "zero Django imports in packing/" idea is one I want to be able to
  defend as my own design choice, which I can, because I understood and
  agreed with the reasoning before it was built, not after.
- The free-space guillotine packing algorithm and its non-overlap proof
  (see `docs/ALGORITHM.md`) — I worked through the proof by hand against
  the actual code before accepting it, rather than trusting the comment.
- The 4-stage funnel (weight → volume → item-too-large → geometry) and the
  cost-then-utilization-then-code tie-break.
- The isometric SVG visualizer approach (hand-rolled projection math, no
  charting library) — I specifically wanted something I could explain line
  by line, not a `matplotlib`/`three.js` black box.

## What I rejected or made it change

- **DEMO-005 seed data originally used 6 monitors to demonstrate a
  "nothing fits" order.** When actually run, the multi-box fallback
  correctly split them across 3 boxes (2 monitors each) instead of failing
  — a genuinely *good* result, but not what that demo order was supposed to
  show. I had it replace the scenario with a treadmill sized larger than
  every box's inner dimensions on every axis, which is the correct way to
  construct a guaranteed-no-fit case. This surfaced because the tool ran
  the actual recommendation against the seeded data and printed the result,
  rather than asserting behavior it hadn't executed.
- **The example numbers in `README.md`** were initially written from memory
  of an earlier test run instead of the exact live output. I had it re-run
  the actual `curl` request and correct the JSON example to match — the
  book's placement position/orientation in the plan was different from what
  had been guessed.

## Mistakes the AI made (and how they were caught)

This is the section I actually care about — every one of these is a real
thing that happened in this build, not a hypothetical.

1. **Sequencing bug:** `config/urls.py` was written referencing
   `api.urls`/`api.web_urls` before those files existed, because the URL
   config was drafted ahead of the app that resolves it. `manage.py
   makemigrations` failed immediately with `ModuleNotFoundError`. Caught
   the moment it was run — fixed by adding placeholder `urlpatterns = []`
   files, filled in properly once the API app was actually built (Phase 5).
2. **A reasoning error in a test's setup comment**, not just the code: an
   early draft of `test_geometric_rejection_when_items_individually_fit_but_not_together`
   picked item dimensions where the total volume *also* exceeded the box
   (so it would have been rejected at the VOLUME stage, not proving what
   the test claimed to prove — that geometry catches something volume
   can't). This was caught by hand-checking the arithmetic in the comment
   against what the code would actually do, before running it — and
   replaced with two 6×6×6 cubes in a 10×10×6 box, where volume fits
   (432mm³ of 600mm³) but geometry genuinely can't arrange both at once.
3. **A leftover broken assertion in `tests/test_api.py`** from a mid-edit —
   a line of nonsense token-soup (`body["recommended_box"]["box"" ".strip()...`)
   that isn't valid reasoning even though it happened to be syntactically
   parseable Python. Caught on review before running the suite, deleted.
4. **Lint findings that were real, not stylistic nitpicks:** `ruff` caught
   an unused variable (`heavy_mug` created but never referenced — dead
   setup code in a test), several `dict(...)` calls that should have been
   literals, and lines over the 100-column limit. All fixed; `ruff check .`
   is clean in this repo (verified in `TEST_OUTPUT.md`).
5. **One deliberate rule override, not a mistake:** `ruff` also flagged
   every use of `l` for "length" as an ambiguous variable name (`E741`).
   Rather than rename it everywhere to `length` (noisier, and `l/w/h`
   already reads clearly against `packing/dimensions.py`'s `Dimensions`
   type), I had it add a scoped, commented `ignore` in `pyproject.toml`
   explaining why. That's a call I made, not something accepted silently.

## A genuine (not manufactured) finding, worth calling out

While building the demo seed data, `DEMO-001` (a ceramic mug + a paperback
book) turned out to be rejected from the cheapest box (`S`) even though
their *combined volume* fits comfortably — 1.45M mm³ of a 5.4M mm³ interior.
The reason, once traced through: the mug is placed first (larger volume),
and no orientation of it leaves 198mm free along any axis of the remaining
space — but the book's longest edge is 198mm. This is a real limitation of
the greedy, non-backtracking packing heuristic (documented honestly in
`docs/ALGORITHM.md` → "Known limitations"), not a bug I asked to be hidden.
I chose to keep this in the demo data and document it rather than swap in
an example that made the algorithm look flawless — it's a more honest and
more interesting thing to be able to explain in an interview than a case
where everything just works.

## How the final code was verified

Nothing in this repo is "trust me, the AI said it works":

- **`pytest -v`** — 54 tests, all passing, real output captured in
  `TEST_OUTPUT.md` from an actual run, not written by hand.
- **`ruff check .`** — clean.
- **`python manage.py makemigrations --check --dry-run`** — no drift
  between models and migrations.
- **Manual API/browser verification** — the dev server was actually started
  and `curl`'d (`/api/v1/recommend/`, `/api/v1/orders/{id}/recommend/`),
  the admin and Swagger UI were hit over HTTP, and the `/visualize/<id>/`
  page was fetched and checked for a real SVG count in the response body,
  not just a 200 status code.
- **The rod-in-a-cube test** (`tests/test_fit.py`) was specifically
  designed, before the fit engine existed, as the thing a naive volume-only
  implementation would fail — and it's the first test I'd point to as proof
  the "geometry, not arithmetic" claim in the README isn't just marketing.
- **A fuzz test with a fixed seed** (`test_random_packings_never_violate_geometry_invariants`,
  seed `20260806`) packs 200 random item sets and asserts the physical
  invariants (in-bounds, non-overlapping) on every one — this is what
  actually gives confidence the free-space split logic is correct in
  general, not just on the hand-picked examples.

## What the AI was deliberately not allowed to do

- Write `LEARNINGS.md` — the assignment requires this be my own, unaided
  answer, and says so explicitly.
- Write or fabricate the chat transcript export — that's this real session,
  exported as-is, not a written-after-the-fact narrative.
- Make the final call on scope, repo visibility, or the Python install —
  those were mine (see the questions table above); the tool's job was to
  execute well and flag trade-offs, not decide for me.
