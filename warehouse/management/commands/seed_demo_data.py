"""Seeds a small, realistic catalogue plus a few demo orders — including
deliberately awkward products (a poster tube, a floor mat) that exist
specifically to exercise the geometric fit checks, not just volume."""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from warehouse.models import Box, Order, OrderItem, Product

BOXES = [
    {"code": "XS", "name": "Extra Small Carton", "inner_length_mm": 150, "inner_width_mm": 100,
         "inner_height_mm": 80, "max_weight_g": 1000, "cost": Decimal("15.00")},
    {"code": "S", "name": "Small Carton", "inner_length_mm": 250, "inner_width_mm": 180,
         "inner_height_mm": 120, "max_weight_g": 3000, "cost": Decimal("25.00")},
    {"code": "M", "name": "Medium Carton", "inner_length_mm": 350, "inner_width_mm": 250,
         "inner_height_mm": 200, "max_weight_g": 8000, "cost": Decimal("40.00")},
    {"code": "L", "name": "Large Carton", "inner_length_mm": 500, "inner_width_mm": 400,
         "inner_height_mm": 300, "max_weight_g": 15000, "cost": Decimal("65.00")},
    {"code": "XL", "name": "Extra Large Carton", "inner_length_mm": 700, "inner_width_mm": 500,
         "inner_height_mm": 450, "max_weight_g": 25000, "cost": Decimal("95.00")},
    {"code": "FLAT", "name": "Flat Mailer", "inner_length_mm": 350, "inner_width_mm": 250,
         "inner_height_mm": 30, "max_weight_g": 1500, "cost": Decimal("12.00")},
    {"code": "TUBE", "name": "Postal Tube", "inner_length_mm": 600, "inner_width_mm": 90,
         "inner_height_mm": 90, "max_weight_g": 2000, "cost": Decimal("18.00")},
]

PRODUCTS = [
    {"sku": "MUG-001", "name": "Ceramic Mug",
         "length_mm": 110, "width_mm": 90, "height_mm": 95,
         "weight_g": 350, "fragile": True, "this_side_up": False},
    {"sku": "BOOK-001", "name": "Paperback Novel",
         "length_mm": 198, "width_mm": 129, "height_mm": 20,
         "weight_g": 280, "fragile": False, "this_side_up": False},
    {"sku": "TSHIRT-001", "name": "Cotton T-Shirt (folded)",
         "length_mm": 280, "width_mm": 220, "height_mm": 25,
         "weight_g": 180, "fragile": False, "this_side_up": False},
    {"sku": "BOTTLE-001", "name": "Glass Water Bottle",
         "length_mm": 75, "width_mm": 75, "height_mm": 240,
         "weight_g": 420, "fragile": True, "this_side_up": True},
    {"sku": "LAPTOP-001", "name": "13-inch Laptop (boxed)",
         "length_mm": 340, "width_mm": 240, "height_mm": 40,
         "weight_g": 1600, "fragile": True, "this_side_up": False},
    {"sku": "POSTER-001", "name": "Rolled Poster (in tube)",
         "length_mm": 580, "width_mm": 80, "height_mm": 80,
         "weight_g": 250, "fragile": False, "this_side_up": False},
    {"sku": "PLATE-001", "name": "Ceramic Dinner Plate",
         "length_mm": 260, "width_mm": 260, "height_mm": 25,
         "weight_g": 650, "fragile": True, "this_side_up": True},
    {"sku": "CABLE-001", "name": "USB-C Cable (boxed)",
         "length_mm": 120, "width_mm": 80, "height_mm": 30,
         "weight_g": 90, "fragile": False, "this_side_up": False},
    {"sku": "YOGA-001", "name": "Rolled Yoga Mat",
         "length_mm": 650, "width_mm": 150, "height_mm": 150,
         "weight_g": 1100, "fragile": False, "this_side_up": False},
    {"sku": "MONITOR-001", "name": "24-inch Monitor (boxed)",
         "length_mm": 580, "width_mm": 420, "height_mm": 180,
         "weight_g": 5200, "fragile": True, "this_side_up": True},
    {"sku": "TREADMILL-001", "name": "Treadmill (crated)",
         "length_mm": 750, "width_mm": 550, "height_mm": 500,
         "weight_g": 45000, "fragile": False, "this_side_up": False},
]

DEMO_ORDERS = [
    # Everyday case: a mug + a book. Should land in a small/medium box.
    {"reference": "DEMO-001", "lines": [("MUG-001", 1), ("BOOK-001", 1)]},
    # The volume trap: a poster tube is long and thin. Total volume is
    # small, but it needs the postal TUBE or something with a long
    # enough axis — a volume-only checker would wrongly suggest XS.
    {"reference": "DEMO-002", "lines": [("POSTER-001", 1)]},
    # Multiple fragile "this side up" bottles + a plate — tests
    # orientation restriction and stacking together.
    {"reference": "DEMO-003", "lines": [("BOTTLE-001", 3), ("PLATE-001", 2)]},
    # A big order that needs MULTI_BOX: several bulky items at once.
    {"reference": "DEMO-004", "lines": [("MONITOR-001", 2), ("YOGA-001", 2), ("LAPTOP-001", 3)]},
    # Genuinely NO_FIT: exceeds every box's inner dimensions on every axis
    # (750x550x500mm is bigger than even the XL carton's 700x500x450mm),
    # so no single box OR combination of boxes can ever hold it.
    {"reference": "DEMO-005", "lines": [("TREADMILL-001", 1)]},
]


class Command(BaseCommand):
    help = "Seed the database with a demo box catalogue, product catalogue, and demo orders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete existing Box/Product/Order rows before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            Order.objects.all().delete()
            Product.objects.all().delete()
            Box.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed existing catalogue/orders."))

        for data in BOXES:
            box, created = Box.objects.update_or_create(code=data["code"], defaults=data)
            self.stdout.write(f"{'Created' if created else 'Updated'} box {box.code}")

        for data in PRODUCTS:
            product, created = Product.objects.update_or_create(sku=data["sku"], defaults=data)
            self.stdout.write(f"{'Created' if created else 'Updated'} product {product.sku}")

        for order_data in DEMO_ORDERS:
            order, created = Order.objects.get_or_create(reference=order_data["reference"])
            if not created:
                order.items.all().delete()
            for sku, qty in order_data["lines"]:
                OrderItem.objects.create(
                    order=order, product=Product.objects.get(sku=sku), quantity=qty
                )
            self.stdout.write(f"{'Created' if created else 'Rebuilt'} order {order.reference}")

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(BOXES)} boxes, {len(PRODUCTS)} products, {len(DEMO_ORDERS)} orders."
        ))
