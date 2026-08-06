"""
The ONE seam between Django and the pure `packing` domain.

Everything above this file (views, management commands, admin actions)
talks to `warehouse` models. Everything below `packing.selector` /
`packing.multibox` talks to plain dataclasses. This module is where the
translation happens, both directions.
"""

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import QuerySet

from packing.dimensions import Dimensions
from packing.entities import Container, Item
from packing.multibox import pack_multi_box
from packing.selector import select_box
from warehouse.models import Box, Order, OrderItem, Recommendation

ALGORITHM_VERSION = "1.0"


@dataclass(frozen=True)
class RecommendationResult:
    """What `recommend_for_order` hands back — a superset of what gets
    persisted, so callers (API views, the CLI command) don't need to
    re-derive anything from a saved Recommendation row."""

    strategy: str
    recommended_box: Box | None
    total_cost: Decimal | None
    utilization: float | None
    plan: list[dict]
    trace: list[dict]


def _box_to_container(box: Box) -> Container:
    return Container(
        code=box.code,
        name=box.name,
        dims=Dimensions(box.inner_length_mm, box.inner_width_mm, box.inner_height_mm),
        max_weight_g=box.max_weight_g,
        cost=box.cost,
    )


def order_items_to_domain_items(order_items: QuerySet[OrderItem]) -> list[Item]:
    """Expand `quantity`-bearing OrderItems into individual packing
    Items — the packer only ever reasons about single indivisible
    objects, never "3 of these"."""
    items: list[Item] = []
    for order_item in order_items.select_related("product"):
        product = order_item.product
        dims = Dimensions(product.length_mm, product.width_mm, product.height_mm)
        for unit in range(order_item.quantity):
            items.append(
                Item(
                    id=f"{product.sku}#{unit}",
                    sku=product.sku,
                    name=product.name,
                    dims=dims,
                    weight_g=product.weight_g,
                    this_side_up=product.this_side_up,
                    fragile=product.fragile,
                )
            )
    return items


def cart_lines_to_domain_items(lines: list[dict]) -> list[Item]:
    """Same expansion as above, but for the stateless `/recommend/`
    endpoint which takes `{"sku": ..., "quantity": ...}` payloads
    instead of a saved Order."""
    from warehouse.models import Product

    items: list[Item] = []
    skus = [line["sku"] for line in lines]
    products = {p.sku: p for p in Product.objects.filter(sku__in=skus)}
    missing = set(skus) - set(products)
    if missing:
        raise ValueError(f"Unknown SKU(s): {', '.join(sorted(missing))}")

    for line in lines:
        product = products[line["sku"]]
        dims = Dimensions(product.length_mm, product.width_mm, product.height_mm)
        for unit in range(line["quantity"]):
            items.append(
                Item(
                    id=f"{product.sku}#{unit}",
                    sku=product.sku,
                    name=product.name,
                    dims=dims,
                    weight_g=product.weight_g,
                    this_side_up=product.this_side_up,
                    fragile=product.fragile,
                )
            )
    return items


def recommend(items: list[Item], allow_multi_box: bool = True) -> RecommendationResult:
    """The framework-agnostic core: given expanded items, run the
    funnel and return a result. Used by both the persisting order-flow
    and the stateless API endpoint."""
    boxes = list(Box.objects.filter(is_active=True))
    containers = [_box_to_container(b) for b in boxes]
    box_by_code = {b.code: b for b in boxes}

    result = select_box(containers, items)

    if result.strategy == "SINGLE_BOX":
        plan = [
            {
                "sku": p.sku,
                "name": p.name,
                "position": list(p.position),
                "dims": [p.placed_dims.length, p.placed_dims.width, p.placed_dims.height],
            }
            for p in result.fit_result.placements
        ]
        return RecommendationResult(
            strategy="SINGLE_BOX",
            recommended_box=box_by_code[result.recommended_box.code],
            total_cost=result.recommended_box.cost,
            utilization=result.fit_result.utilization,
            plan=plan,
            trace=[v.to_dict() for v in result.verdicts],
        )

    # No single box fits — try the multi-box fallback.
    if allow_multi_box and containers:
        multi = pack_multi_box(containers, items)
        if multi.fits:
            plan = [
                {
                    "box": unit.container.code,
                    "items": [
                        {
                            "sku": p.sku,
                            "name": p.name,
                            "position": list(p.position),
                            "dims": [
                                p.placed_dims.length,
                                p.placed_dims.width,
                                p.placed_dims.height,
                            ],
                        }
                        for p in unit.placements
                    ],
                }
                for unit in multi.units
            ]
            return RecommendationResult(
                strategy="MULTI_BOX",
                recommended_box=None,
                total_cost=multi.total_cost,
                utilization=None,
                plan=plan,
                trace=[v.to_dict() for v in result.verdicts],
            )

    return RecommendationResult(
        strategy="NO_FIT",
        recommended_box=None,
        total_cost=None,
        utilization=None,
        plan=[],
        trace=[v.to_dict() for v in result.verdicts],
    )


def recommend_for_order(order: Order, allow_multi_box: bool = True) -> Recommendation:
    """Compute a recommendation for a saved Order and persist it."""
    items = order_items_to_domain_items(order.items.all())
    result = recommend(items, allow_multi_box=allow_multi_box)

    recommendation, _ = Recommendation.objects.update_or_create(
        order=order,
        defaults={
            "strategy": result.strategy,
            "primary_box": result.recommended_box,
            "total_cost": result.total_cost,
            "utilization": result.utilization,
            "plan": result.plan,
            "trace": result.trace,
            "algorithm_version": ALGORITHM_VERSION,
        },
    )

    order.status = Order.Status.NO_FIT if result.strategy == "NO_FIT" else Order.Status.RECOMMENDED
    order.save(update_fields=["status"])

    return recommendation
