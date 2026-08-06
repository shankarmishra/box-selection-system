# The box-selection algorithm

This is the piece I'd walk an interviewer through line by line. Code lives in
`packing/` — zero Django imports, so every claim below is directly testable
in `tests/test_fit.py`, `test_selector.py`, `test_multibox.py`.

## Why not just compare volumes?

Because it's wrong, in a way that's easy to ship by accident:

```
A 300×10×10mm rod:      volume = 30,000 mm³
A 32×32×32mm cube box:  volume = 32,768 mm³
```

`30,000 < 32,768` — a volume check says the rod fits. It physically can't:
the rod is 300mm long and the box's longest edge is 32mm. There is no
orientation where it fits. This is `tests/test_fit.py::test_volume_is_not_enough_a_rod_does_not_fit_in_a_smaller_volume_cube`,
and it's the reason this project does real geometry instead of arithmetic.

## The funnel

Every catalogue box runs through 4 stages, cheapest first, so we never pay
for a geometric simulation on a box that's obviously too small:

```
┌──────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│  1. WEIGHT   │──▶│  2. VOLUME   │──▶│ 3. ITEM TOO LARGE │──▶│ 4. GEOMETRY  │
│  O(1)        │   │  O(n)        │   │  O(n × 6)         │   │  O(n² × 6)   │
└──────────────┘   └──────────────┘   └──────────────────┘   └──────────────┘
  order weight       Σ item volumes     does EVERY item fit    can everything be
  > box max?          > box volume?     the box in SOME         arranged inside
                                         rotation, alone?        SIMULTANEOUSLY?
```

Stages 1–3 are cheap rejects with a precise, human-readable reason attached
(`packing/trace.py`). Stage 4 — the actual simulation — only runs for boxes
that survive all three.

## Stage 4: the free-space guillotine packer

Optimal 3D bin-packing is NP-hard, so this is a **greedy, first-fit,
best-leftover heuristic** — not a solver. It's deliberately simple enough to
draw on a whiteboard:

1. Start with **one** free cuboid: the whole box interior.
2. Sort items largest-volume-first (this is a resemblance to
   First-Fit-Decreasing).
3. For each item, try **every free cuboid × every allowed rotation** (6 for
   free items, 2 for `this_side_up` items — see below) and place it in
   whichever combination **wastes the least volume**.
4. Placing an item always uses the free space's minimum corner — that one
   choice is what makes the next step provably correct.
5. Split the *remaining* volume of that free space into exactly 3 new
   non-overlapping cuboids. Repeat.

### Why the split is provably non-overlapping

Say a free cuboid has origin `(x,y,z)` and size `(L,W,H)`. We place an item
of size `(l,w,h)` at that same origin. The leftover volume splits into:

```
   z              ┌─────────────┐
   │             ╱│      C      │
   │            ╱ │  (l, w, H-h)│
   │           ╱  └─────────────┘
   │          ╱  ┌───────────────────────────┐
   │      ┌──┴──┐│            B               │
   │      │item │  (l, W-w, H)                │
   │      │(l,w,│└───────────────────────────┘
   │      │ h)  │
   │      └─────┘┌─────────────────────────────────┐
   │              │              A                  │
   │              │         (L-l, W, H)              │
   └──────────────┴──────────────────────────────────┴──▶ x
```

- **A** (x-remainder): origin `(x+l, y, z)`, size `(L-l, W, H)`
- **B** (y-remainder): origin `(x, y+w, z)`, size `(l, W-w, H)`
- **C** (z-remainder): origin `(x, y, z+h)`, size `(l, w, H-h)`

A's x-range `[x+l, x+L)` never overlaps B or C (both live in `[x, x+l)`).
B's y-range `[y+w, y+W)` never overlaps C (which lives in `[y, y+w)`).
So A, B, C, and the placed item are **pairwise disjoint by construction**.
Volume check: expand `(L-l)WH + l(W-w)H + lw(H-h)` and the cross terms
cancel to `LWH - lwh` — exactly the leftover, no double-counting.

Since the box interior starts as a single free region (trivially
non-overlapping with nothing else) and every operation preserves the
invariant, **the free-space list can never contain overlapping regions** —
by induction. That's what stops the packer from ever reporting two items in
the same physical spot. `tests/test_fit.py::test_random_packings_never_violate_geometry_invariants`
fuzzes this with 200 random item sets and a fixed seed (`20260806`) and
asserts it on every run.

### Rotations

`packing/dimensions.py::rotations()`:
- **Free items**: all 6 permutations of `(length, width, height)` — every
  face can be "down."
- **`this_side_up` items** (liquids, fragile-and-marked): only 2 rotations —
  the height axis never moves, only length/width can swap around the
  vertical axis.

## Stage 5: multi-box fallback

If no single box fits, `packing/multibox.py` runs a greedy bin-selection
loop: each round, simulate packing the *remaining* items into every box
type (the real 3D packer, not a volume guess), score each by
`packed_volume / cost`, and commit to one instance of the best-scoring box.
Repeat until nothing is left, or a round packs zero items (meaning
something fits no box at all, at any size).

## The explainability trace

Every response — API, CLI, visualizer — includes a verdict for **every**
box, not just the winner:

```json
{"box": "S", "verdict": "REJECTED", "stage": "geometry",
 "reason": "no space left for: Paperback Novel"}
```

This is `packing/trace.py` + `packing/selector.py::evaluate_box()`. A
warehouse operator (or an interviewer) can see exactly why box S lost to
box M — not just that it did.

## Deterministic tie-breaking

Feasible boxes are ranked: **cheapest cost** → **highest utilization**
(tighter pack = less wasted dimensional weight) → **box code**
(alphabetical, as a last resort). Every tie-break is a pure function of the
inputs, so the same order always produces the same recommendation.

## Known limitations (the honest list)

1. **Greedy ≠ optimal — false negatives are possible.** The packer can
   reject a box that a cleverer algorithm could still pack. This is a *real,
   reproducible* result from this project's own seed data: order `DEMO-001`
   (a mug + a paperback book) is rejected from box `S` even though total
   item volume fits comfortably (1.45M mm³ into 5.4M mm³ of interior). Why:
   the mug (larger volume) is placed first, and whichever orientation it
   takes always leaves less than 198mm free along every axis of the
   remaining space — but the book's longest edge is 198mm. A smarter
   packer that tried "book first" would succeed. This one doesn't backtrack.
   Run `python manage.py recommend_box --order DEMO-001` to see it live.

2. **The asymmetry is deliberate, not a bug.** A false negative costs the
   warehouse one box size up (safe, slightly pricier). A false positive
   would cost a failed pack on the floor and a re-ship (expensive, and
   erodes trust in the system). Every design choice here — the conservative
   split, the greedy-not-backtracking search — biases toward the cheap
   error. See `docs/DESIGN_DECISIONS.md`.

3. **No rotation-invariant caching / no branch-and-bound.** For catalogues
   with dozens of items per order, this would start to matter. At the scale
   of a typical parcel order (a handful of items), it's fast (sub-millisecond
   in the test suite) and not worth the complexity.

4. **Multi-box fallback isn't cost-optimal.** It's a greedy best-value-per-
   round heuristic, not a true bin-packing solver — it will usually produce
   a good split, not necessarily the cheapest possible one.

5. **Fragile items aren't packed with any stacking-order preference** (e.g.
   "don't put heavy things on top of fragile things"). The `fragile` flag is
   captured on `Product` and threaded through to `Item`, but the packer
   doesn't currently use it. A natural next step.
