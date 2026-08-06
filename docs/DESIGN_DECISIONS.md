# Design decisions

Short ADR-style records of the calls that shaped this project, in the order
they'd come up in an interview.

---

### 1. Integer millimetres and grams, not floats

**Decision:** every dimension is an integer mm, every weight an integer g.
Cost is `Decimal`, never `float`.

**Why:** fit checks are pure `a <= b` comparisons. With floats, `0.1 + 0.2
!= 0.3`-style errors mean two numbers that should tie (or should just-barely
fit) can silently go either way depending on floating-point representation.
Integer millimetres make every comparison exact — no epsilon fudging
anywhere in the geometry. Real-world product dimensions are precise to the
millimetre anyway (nobody measures a box to 0.001mm), so nothing is lost.
`Decimal` for cost is the standard "never use float for money" rule.

**Trade-off:** callers must round dimensions to the millimetre before
calling the API. Fine for this domain.

---

### 2. `packing/` has zero Django imports

**Decision:** the packing/selection engine is plain-dataclass in, plain-
dataclass out. `warehouse/services.py` is the only file that touches both
the ORM and `packing`.

**Why:** the algorithm is the actual assignment. It needs to be testable in
milliseconds without spinning up a database, and portable — if this ever
needed to run in a Celery worker, a serverless function, or a different web
framework entirely, the core logic moves unchanged. It also makes the test
suite fast enough that `pytest -v` over 77 tests runs in well under a
second, which matters when you're iterating on the algorithm itself.

**Trade-off:** one extra translation layer (`services.py`). Worth it.

---

### 3. Guillotine free-space splitting, not extreme-point or maximal-rectangles

**Decision:** the fit engine uses a simple free-space list with an exact
3-way guillotine split (see `docs/ALGORITHM.md`), not a more sophisticated
3D bin-packing algorithm.

**Why:** it's provably correct (see the non-overlap proof in
`ALGORITHM.md`) and small enough to explain — and re-derive — on a
whiteboard in about a minute. More sophisticated approaches (extreme-point
heuristics, maximal-rectangles, branch-and-bound) pack tighter and avoid
some of this algorithm's false negatives, but they're meaningfully harder
to reason about and to keep provably correct. For a take-home assignment
where the whole point is "does the candidate understand what they built,"
optimizing for explainability over packing density was the right call.

**Trade-off:** documented and accepted — see "Known limitations" in
`ALGORITHM.md`. The DEMO-001 case (mug + book rejected from box S despite
volume fitting comfortably) is a real, reproducible example.

---

### 4. Conservative bias: false negatives over false positives

**Decision:** every choice in the algorithm — greedy non-backtracking
search, first-fit-decreasing item order, exact geometric checks — is biased
toward *rejecting a box that might actually work* rather than *accepting a
box that doesn't*.

**Why:** the two error types have very different costs in a warehouse. A
false negative means the system suggests a box one size up — mildly more
expensive, no operational impact. A false positive means a picker gets
handed a box, discovers mid-pack that the items don't physically fit, and
has to stop, unpack, and start over with a bigger box — wasted labor, a
delayed shipment, and (worse) eroded trust in the recommendation system
itself. Given that asymmetry, biasing cheap-and-safe over
tight-and-risky is the right trade every time.

---

### 5. Cost first, then utilization, then box code — never "biggest box"

**Decision:** selection ranks strictly by `(cost, -utilization, box_code)`.

**Why:** cost is what the business actually cares about minimizing. Tighter
utilization is the tie-breaker because it correlates with lower dimensional
weight (courier billing) and less void-fill material — a real secondary
cost even at equal box price. Box code as the final tie-break exists purely
so results are 100% deterministic; two runs with the same catalogue and
order always produce the same answer, which matters for testing and for
warehouse staff trusting the system won't flip-flop.

---

### 6. Every box gets a verdict, not just the winner

**Decision:** `evaluate_box()` runs and records a verdict for every active
box in the catalogue, and the API/CLI/visualizer all surface the full list.

**Why:** this is the single feature I'd point to as "why is this different
from a checkbox implementation." A black-box "here's your box" answer is
useless to a warehouse operator who needs to understand *why* the system
didn't pick the cheaper option sitting right next to them, and useless to
me in an interview trying to prove the geometry is doing real work and not
a coin flip. It costs almost nothing extra to compute (the funnel already
evaluates every box) — the only added cost is capturing *why* at each
rejection point instead of just a boolean.

---

### 7. No third-party bin-packing library (`py3dbp` etc.)

**Decision:** the packing engine is hand-written, not a dependency.

**Why:** the packing algorithm is explicitly the assignment. Pulling in a
library would answer the letter of the brief while skipping the part that's
actually being evaluated. See `AI_USAGE.md` for the point in the build where
this was directly considered and rejected.

---

### 8. SQLite, not Postgres

**Decision:** the demo ships on SQLite with no configuration required.

**Why:** zero setup for a take-home reviewer (`git clone && run`, no
docker-compose required just to see it work). The models use only
standard Django field types (no JSONField-specific Postgres features
beyond what SQLite's JSON1 extension already supports via Django's ORM),
so swapping `DATABASES` to Postgres would be a one-line config change if
this went to production — nothing in `warehouse/` or `packing/` assumes a
specific backend.

---

### 9. What would change at 10x scale (order volume, catalogue size, or item count per order)

Honest answer, since this will likely come up:

- **More orders per second:** the algorithm is pure and stateless per
  request, so it horizontally scales trivially — no changes needed beyond
  standard Django scaling (more app servers, connection pooling).
- **Much larger box catalogues (hundreds of SKUs):** stage 1–3 rejects stay
  O(1)/O(n) per box regardless, so this scales linearly and is fine. Could
  add a cheap pre-filter (e.g. skip boxes whose volume is less than the
  order's total item volume) before even running stage 1, though that's
  already what stage 2 does.
- **Many items per order (dozens+):** this is where the guillotine
  packer's O(n² × 6) per-box cost would start to matter, and where
  swapping in a proper extreme-point or branch-and-bound packer — or
  caching sub-results — would become worth the added complexity discussed
  in decision #3.
- **Multi-box optimality:** the current greedy fallback would be the first
  thing I'd revisit — a proper set-cover / ILP formulation would produce
  genuinely cost-optimal splits instead of "good enough."
