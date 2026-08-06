# 📦 Box Selection System

A Django + DRF service that recommends the cheapest shipping box that can
**physically** hold an order — not just one whose volume adds up. Given an
order's products (each with dimensions + weight) and a box catalogue (inner
dimensions, max weight, cost), it runs a real 3D geometric simulation and
returns the cheapest box that fits, along with a full explanation of why
every *other* box in the catalogue was accepted or rejected.

Built for a Django hiring assignment. See [`AI_USAGE.md`](AI_USAGE.md) for
how AI tools were used, [`LEARNINGS.md`](LEARNINGS.md) for what I took away
from it, and [`docs/ALGORITHM.md`](docs/ALGORITHM.md) for the full write-up
of how the packer works.

## Why this isn't just "sum the volumes"

A 300×10×10mm rod has a volume of 30,000 mm³. A 32×32×32mm cube has a volume
of 32,768 mm³. A volume check says the rod fits. It doesn't — the rod is
300mm long and the box's longest edge is 32mm. This project exists because
that check is wrong, and it's easy to accidentally ship it. See
[`tests/test_fit.py::test_volume_is_not_enough_a_rod_does_not_fit_in_a_smaller_volume_cube`](tests/test_fit.py)
for the executable proof, and `docs/ALGORITHM.md` for how the real packer
avoids it.

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

## The algorithm, in one paragraph

Every candidate box runs through a 4-stage funnel, cheapest checks first:
**weight** (reject if the order is too heavy), **volume** (reject if total
item volume exceeds the box), **item-too-large** (reject if any single item
fits in no orientation), then — only for survivors — a real **geometric
simulation**: a free-space guillotine 3D packer that tries every item in
every rotation against every remaining free region, and only claims success
if literally everything fits simultaneously. The cheapest surviving box
wins; ties break on tighter packing (less wasted volume), then box code, so
results are 100% deterministic. If nothing fits in one box, a greedy
multi-box fallback splits the order across several. Full write-up with
diagrams: [`docs/ALGORITHM.md`](docs/ALGORITHM.md).

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
    {"box": "S", "verdict": "REJECTED", "stage": "geometry", "reason": "All items individually fit, and total volume fits, but they can't be simultaneously arranged inside box S — no space left for: Paperback Novel", ...},
    {"box": "M", "verdict": "SELECTED", "cost": "40.00", "utilization": 0.0829, ...},
    {"box": "L", "verdict": "FITS_BUT_COSTLIER", "cost": "65.00", ...},
    ...
  ]
}
```

`evaluated` is the differentiator: every box in the catalogue is explained,
not just the winner. That "box S rejected — no space left for the novel" is
a real result from this catalogue, and a genuinely interesting one — see
"Known limitations" in `docs/ALGORITHM.md` for why.

## The packing visualizer

`GET /visualize/<order_id>/` renders each recommended box as an isometric
SVG (with fake per-face lighting) plus flat top/front/side projections,
alongside the full trace table. Pure Python — no charting library, no JS, no
CDN — see [`api/visualizer.py`](api/visualizer.py).

## Tests

```bash
pytest -v                    # 54 tests
pytest --cov=packing --cov=warehouse --cov=api --cov-report=term-missing
ruff check .                 # lint
python manage.py makemigrations --check --dry-run   # migration drift
```

Real output from a full run: [`TEST_OUTPUT.md`](TEST_OUTPUT.md). CI runs the
same on every push: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Test layout:
- `tests/test_dimensions.py`, `test_fit.py`, `test_selector.py`,
  `test_multibox.py` — the pure `packing/` engine, no database required
- `tests/test_models.py`, `test_services.py` — the ORM ↔ domain adapter
- `tests/test_api.py` — the DRF endpoints end to end

## Project structure

```
packing/          pure domain: dimensions, fit engine, selection funnel, multi-box, trace
warehouse/         Django app: models, admin, services.py (the ORM<->domain seam), seed data
api/               Django app: DRF views/serializers, SVG visualizer, web pages
config/            Django project settings/urls
tests/             pytest suite (54 tests)
docs/               ALGORITHM.md, DESIGN_DECISIONS.md
```

## Known limitations

See `docs/ALGORITHM.md` → "Known limitations" for the honest list (greedy
packing can produce false negatives; no rotation-invariant caching; the
multi-box fallback isn't cost-optimal). None of these produce a false
positive — the packer never claims a fit that's physically impossible,
which was the deliberate design bias.
