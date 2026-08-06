from django.shortcuts import get_object_or_404, render
from django.views import View

from warehouse.models import Box, Order
from warehouse.services import recommend_for_order

from .visualizer import render_isometric_svg, render_orthographic_svg


class HomeView(View):
    """A minimal index page: link to the API docs, the admin, and the
    visualizer for every seeded order — the fastest way to demo the
    whole system without needing curl."""

    def get(self, request):
        orders = Order.objects.all()[:50]
        return render(request, "api/home.html", {"orders": orders})


class VisualizeOrderView(View):
    """Renders the packing plan for an order as isometric + orthographic
    SVGs, one card per physical box, alongside the full explainability
    trace. Computes the recommendation on the fly if it hasn't been
    run yet (this page is meant to "just work" from a fresh clone)."""

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        recommendation = getattr(order, "recommendation", None)
        if recommendation is None:
            recommendation = recommend_for_order(order)

        box_cards = []
        if recommendation.strategy == "SINGLE_BOX":
            box = recommendation.primary_box
            box_cards.append(_build_card(box, recommendation.plan, recommendation.utilization))
        elif recommendation.strategy == "MULTI_BOX":
            boxes_by_code = {b.code: b for b in Box.objects.filter(
                code__in=[unit["box"] for unit in recommendation.plan]
            )}
            for unit in recommendation.plan:
                box = boxes_by_code[unit["box"]]
                box_cards.append(_build_card(box, unit["items"], utilization=None))

        context = {
            "order": order,
            "recommendation": recommendation,
            "box_cards": box_cards,
        }
        return render(request, "api/visualize.html", context)


def _build_card(box: Box, plan_items: list[dict], utilization: float | None) -> dict:
    dims = (box.inner_length_mm, box.inner_width_mm, box.inner_height_mm)
    return {
        "box": box,
        "utilization": utilization,
        "items": plan_items,
        "isometric_svg": render_isometric_svg(dims, plan_items),
        "top_svg": render_orthographic_svg(dims, plan_items, "top"),
        "front_svg": render_orthographic_svg(dims, plan_items, "front"),
        "side_svg": render_orthographic_svg(dims, plan_items, "side"),
    }
