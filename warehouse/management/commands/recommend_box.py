"""Terminal-only way to see the full explainability trace for an order
— useful for demoing the system without a browser open."""

from django.core.management.base import BaseCommand, CommandError

from warehouse.models import Order
from warehouse.services import recommend_for_order

COL_WIDTHS = (10, 10, 10, 60)


def _row(*cols: str) -> str:
    return "  ".join(str(c).ljust(w) for c, w in zip(cols, COL_WIDTHS, strict=False))


class Command(BaseCommand):
    help = "Print the box recommendation + full explainability trace for an order."

    def add_arguments(self, parser):
        parser.add_argument("--order", required=True, help="Order reference, e.g. DEMO-001")

    def handle(self, *args, **options):
        try:
            order = Order.objects.get(reference=options["order"])
        except Order.DoesNotExist as exc:
            raise CommandError(f"No order with reference '{options['order']}'") from exc

        recommendation = recommend_for_order(order)

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"Order {order.reference}"))
        self.stdout.write(f"  Strategy:    {recommendation.strategy}")
        if recommendation.strategy == "SINGLE_BOX":
            self.stdout.write(f"  Box:         {recommendation.primary_box.code} "
                               f"({recommendation.primary_box.name})")
            self.stdout.write(f"  Cost:        {recommendation.total_cost}")
            self.stdout.write(f"  Utilization: {recommendation.utilization:.0%}")
        elif recommendation.strategy == "MULTI_BOX":
            self.stdout.write(f"  Boxes used:  {len(recommendation.plan)}")
            self.stdout.write(f"  Total cost:  {recommendation.total_cost}")
        else:
            self.stdout.write(self.style.ERROR("  No box (or combination) fits this order."))

        self.stdout.write("")
        self.stdout.write(_row("Box", "Verdict", "Stage", "Reason"))
        self.stdout.write("-" * sum(COL_WIDTHS))
        for v in recommendation.trace:
            style = self.style.SUCCESS if v["verdict"] == "SELECTED" else (
                self.style.ERROR if v["verdict"] == "REJECTED" else self.style.WARNING
            )
            self.stdout.write(style(_row(v["box"], v["verdict"], v["stage"], v["reason"])))
        self.stdout.write("")
