"""
Catalogue and order models.

Dimensions are stored in **millimetres** and weight in **grams** as
plain `PositiveIntegerField`s — matching the integer-only maths in
`packing/`. See docs/DESIGN_DECISIONS.md for why.

These models are intentionally "dumb" — no packing logic lives here.
`warehouse/services.py` is the only place that converts these rows into
`packing.entities` dataclasses and back.
"""

from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    length_mm = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    width_mm = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    height_mm = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    weight_g = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    fragile = models.BooleanField(default=False)
    this_side_up = models.BooleanField(
        default=False,
        help_text="If set, this item may only be rotated around its vertical "
        "axis (e.g. bottles/liquids) — it can never be laid on its side.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sku"]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"

    @property
    def volume_mm3(self) -> int:
        return self.length_mm * self.width_mm * self.height_mm


class Box(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    inner_length_mm = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    inner_width_mm = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    inner_height_mm = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    max_weight_g = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive boxes are excluded from new recommendations "
        "(e.g. discontinued packaging) but stay visible on old ones.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["cost", "code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    @property
    def volume_mm3(self) -> int:
        return self.inner_length_mm * self.inner_width_mm * self.inner_height_mm


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RECOMMENDED = "RECOMMENDED", "Recommended"
        NO_FIT = "NO_FIT", "No box fits"

    reference = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.reference


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"], name="unique_product_per_order"
            )
        ]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product.sku} (order {self.order.reference})"


class Recommendation(models.Model):
    """A persisted result of running the packing engine against an
    Order. `trace` and `plan` store the full explainability output as
    JSON so the API and the visualizer can render it without
    recomputing anything."""

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="recommendation")
    strategy = models.CharField(max_length=16)  # SINGLE_BOX | MULTI_BOX | NO_FIT
    primary_box = models.ForeignKey(
        Box, on_delete=models.PROTECT, null=True, blank=True, related_name="recommendations"
    )
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    utilization = models.FloatField(null=True, blank=True)
    plan = models.JSONField(default=list)
    trace = models.JSONField(default=list)
    algorithm_version = models.CharField(max_length=16, default="1.0")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Recommendation for {self.order.reference} ({self.strategy})"
