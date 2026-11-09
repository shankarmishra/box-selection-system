# 📦 Box Selection System

A Django + DRF service that recommends the cheapest shipping box that can
**physically** hold an order — not just one whose volume adds up. Given an
order's products (each with dimensions + weight) and a box catalogue (inner
dimensions, max weight, cost), it runs a real 3D geometric simulation and
returns the cheapest box that fits, along with a full explanation of why
every *other* box in the catalogue was accepted or rejected.

Built for a Django hiring assignment. See [`AI_USAGE.md`](AI_USAGE.md) for
how AI tools were used, [`LEARNINGS.md`](LEARNINGS.md) for what I took away
from it.

## Why this isn't just "sum the volumes"

A 300×10×10mm rod has a volume of 30,000 mm³. A 32×32×32mm cube has a volume
of 32,768 mm³. A volume check says the rod fits. It doesn't — the rod is
300mm long and the box's longest edge is 32mm. This project exists because
that check is wrong, and it's easy to accidentally ship it. See
[`tests/test_fit.py::test_volume_is_not_enough_a_rod_does_not_fit_in_a_smaller_volume_cube`](tests/test_fit.py)
for the executable proof.

## Quickstart

```bash
git clone <this-repo>
cd box-selection-system
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Then open:

- **http://127.0.0.1:8000/** — home page, links to every demo order's packing visualization
- **http://127.0.0.1:8000/api/docs/** — interactive Swagger UI for the whole API
- **http://127.0.0.1:8000/admin/** — Django admin for the catalogue (`python manage.py createsuperuser` first)

Or skip the browser entirely:

```bash
python manage.py recommend_box --order DEMO-001
```

## Architecture

```
        HTTP / CLI                 api/           DRF views, serializers,
             │                                     SVG visualizer, mgmt commands
             ▼
   ORM  ── adapter ──►            warehouse/       Product, Box, Order, OrderItem,
             │                                      Recommendation, admin, services.py
             ▼
   pure domain, zero               packing/        dimensions, fit engine, selection
   Django imports                                   funnel, multi-box fallback, trace
```

`warehouse/services.py` is the **only** seam between Django and the packing
engine — it maps ORM rows into plain dataclasses, calls `packing.selector`,
and maps the result back. Everything under `packing/` is pure Python: no
database, no Django imports, runs and unit-tests in milliseconds. That's
deliberate — the packing algorithm is the actual assignment, so it needed to
be trivially testable and, if it ever needed to move into a Celery worker or
a serverless function, portable without touching a line of it.

## How the algorithm works

Every candidate box runs through a 4-stage funnel, cheapest checks first:

```
┌──────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│  1. WEIGHT   │──▶│  2. VOLUME   │──▶│ 3. ITEM TOO LARGE │──▶│ 4. GEOMETRY  │
└──────────────┘   └──────────────┘   └──────────────────┘   └──────────────┘
  order weight       Σ item volumes     does EVERY item fit    can everything be
  > box max?          > box volume?     the box in SOME         arranged inside
                                         rotation, alone?        SIMULTANEOUSLY?
```

Stages 1–3 are cheap O(1)/O(n) rejects, each with a precise human-readable
reason attached. Stage 4 — the real geometric simulation — only runs for
boxes that survive the first three, so we never pay for it on an obviously
too-small box.

**Stage 4, the free-space guillotine packer** (`packing/fit.py`): start with
one free cuboid — the whole box interior. Sort items largest-first. For each
item, try every free cuboid × every allowed rotation (6 for free items, 2
for `this_side_up` items like bottles — only the vertical axis stays fixed),
and place it wherever it wastes the least volume. Then split the *remaining*
space into exactly 3 new non-overlapping cuboids:

- **A** (x-remainder): `origin (x+l, y, z)`, size `(L-l, W, H)`
- **B** (y-remainder): `origin (x, y+w, z)`, size `(l, W-w, H)`
- **C** (z-remainder): `origin (x, y, z+h)`, size `(l, w, H-h)`

These three regions are pairwise disjoint by construction (A's x-range never
overlaps B or C; B's y-range never overlaps C), and their volumes sum
exactly to the leftover — no double-counting, no gaps. Since the box starts
as a single free region and every split preserves that non-overlap property,
**the free-space list can never contain overlapping regions, by induction**.
That's what stops the packer from ever reporting two items in the same
physical spot — proven in code by
`tests/test_fit.py::test_random_packings_never_violate_geometry_invariants`,
which fuzzes 200 random item sets (fixed seed `20260806`) and asserts it
holds every time.

This is a **greedy heuristic, not an optimal solver** — 3D bin-packing is
NP-hard, and optimizing for a whiteboard-explainable algorithm over packing
density was a deliberate trade-off (see "A real limitation" below). Every
design choice here is biased toward the **cheap error**: it's fine to
occasionally suggest a box one size up (false negative), but it must never
claim a fit that's physically impossible (false positive) — that's what
costs a warehouse picker a failed pack and a re-ship.

**Selection**: feasible boxes rank by `(cost, -utilization, box_code)` —
cheapest wins, ties break on tighter packing (less wasted dimensional
weight), then alphabetically, so results are 100% deterministic.

**Multi-box fallback** (`packing/multibox.py`): if nothing fits in one box,
greedily fill boxes round-by-round, each round picking whichever box type
packs the most volume-per-rupee of the *remaining* items, using the real 3D
packer as the scoring function (not a volume guess).

### The explainability trace — the actual differentiator

Every response includes a verdict for **every** box in the catalogue, not
just the winner:

```json
{"box": "S", "verdict": "REJECTED", "stage": "geometry",
 "reason": "no space left for: Paperback Novel"}
```

A warehouse operator — or an interviewer — can see exactly *why* box S lost
to box M, not just that it did. It costs almost nothing extra to compute
(the funnel already evaluates every box); the only added work is capturing
*why* at each rejection point instead of a boolean.

## A real limitation (found and kept, not hidden)

`DEMO-001` (a mug + a paperback book) is rejected from the cheapest box (S)
even though their combined volume fits comfortably — 1.45M mm³ into 5.4M mm³
of interior. Why: the mug (bigger volume) is placed first, and no
orientation of it leaves the book's required 198mm free along any axis of
the leftover space. A smarter, backtracking packer would try "book first"
and succeed; this one doesn't backtrack. Run
`python manage.py recommend_box --order DEMO-001` to see it live — it's a
genuine, reproducible result from this project's own algorithm, and a more
interesting thing to explain than a case where everything just works.

## Key design decisions (short version)

| Decision | Why |
|---|---|
| Integer mm/g, `Decimal` cost — never floats | Fit checks are exact `<=` comparisons; floats introduce epsilon bugs that could silently flip a just-barely-fits result |
| `packing/` has zero Django imports | The algorithm is the actual assignment — needs to be testable in milliseconds and portable to a worker/serverless process unchanged |
| Guillotine split, not extreme-point/maximal-rectangles | Provably correct (see the proof above) and small enough to re-derive on a whiteboard; trades some packing density for explainability |
| Cost → utilization → box code ranking | Cost is what the business minimizes; utilization tie-break correlates with lower dimensional weight and less void-fill; box code makes results fully deterministic |
| No third-party bin-packing library | The packing algorithm is explicitly what's being evaluated — a library would answer the letter of the brief while skipping the point |
| SQLite, not Postgres | Zero-config `git clone && run` for a reviewer; nothing in the code assumes a specific backend, so swapping `DATABASES` is a one-line change |

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/recommend/` | Stateless — `{"items":[{"sku","quantity"}]}` → recommendation + full trace |
| `POST` | `/api/v1/orders/{id}/recommend/` | Compute **and persist** a recommendation for a saved order |
| `GET` | `/api/v1/orders/{id}/recommendation/` | Fetch a previously computed recommendation |
| `GET`/`POST` | `/api/v1/products/`, `/api/v1/boxes/` | Catalogue CRUD |
| `GET` | `/api/v1/health/` | Liveness check |
| `GET` | `/api/docs/` | Swagger UI |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/recommend/ \
  -H "Content-Type: application/json" \
  -d '{"items": [{"sku": "MUG-001", "quantity": 1}, {"sku": "BOOK-001", "quantity": 1}]}'
```

```json
{
  "strategy": "SINGLE_BOX",
  "recommended_box": {"code": "M", "name": "Medium Carton", "cost": "40.00"},
  "total_cost": "40.00",
  "utilization": 0.0829,
  "plan": [
    {"sku": "MUG-001", "name": "Ceramic Mug", "position": [0,0,0], "dims": [110,90,95]},
    {"sku": "BOOK-001", "name": "Paperback Novel", "position": [0,90,0], "dims": [20,129,198]}
  ],
  "evaluated": [
    {"box": "XS", "verdict": "REJECTED", "stage": "volume", "reason": "Items total 1,451,340 mm³; box XS interior is only 1,200,000 mm³", ...},
    {"box": "S", "verdict": "REJECTED", "stage": "geometry", "reason": "...no space left for: Paperback Novel", ...},
    {"box": "M", "verdict": "SELECTED", "cost": "40.00", "utilization": 0.0829, ...},
    {"box": "L", "verdict": "FITS_BUT_COSTLIER", "cost": "65.00", ...}
  ]
}
```

## The packing visualizer

`GET /visualize/<order_id>/` renders each recommended box as an isometric
SVG (with fake per-face lighting) plus flat top/front/side projections,
alongside the full trace table. Pure Python — no charting library, no JS, no
CDN — see [`api/visualizer.py`](api/visualizer.py).

## Tests

```bash
pytest -v                    # 78 tests
pytest --cov=packing --cov=warehouse --cov=api --cov-report=term-missing
ruff check .                 # lint
python manage.py makemigrations --check --dry-run   # migration drift
```

Real output from a full run: [`TEST_OUTPUT.md`](TEST_OUTPUT.md). CI runs the
same on every push: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
Coverage sits at 99% across `packing/`, `warehouse/`, `api/`.

Test layout:
- `tests/test_dimensions.py`, `test_fit.py`, `test_selector.py`,
  `test_multibox.py` — the pure `packing/` engine, no database required
- `tests/test_models.py`, `test_services.py` — the ORM ↔ domain adapter
- `tests/test_api.py` — the DRF endpoints end to end
- `tests/test_web_views.py`, `test_visualizer.py` — the SVG packing pages
- `tests/test_management_commands.py` — `seed_demo_data` and `recommend_box`

## Project structure

```
packing/           pure domain: dimensions, fit engine, selection funnel, multi-box, trace
warehouse/          Django app: models, admin, services.py (the ORM<->domain seam), seed data
api/                Django app: DRF views/serializers, SVG visualizer, web pages
config/             Django project settings/urls
tests/              pytest suite (78 tests)
```

## Known limitations

- Greedy, non-backtracking packing can produce false negatives (see "A real
  limitation" above) — never false positives, which was the deliberate bias.
- No rotation-invariant caching or branch-and-bound — fine at the scale of a
  typical parcel order (sub-millisecond per box in the test suite); would
  start to matter with dozens of items per order.
- The multi-box fallback is a greedy heuristic, not a cost-optimal solver.
- The `fragile` flag is captured on `Product` but not yet used to influence
  stacking order — a natural next step.
