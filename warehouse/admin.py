from django.contrib import admin

from warehouse.models import Box, Order, OrderItem, Product, Recommendation


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "length_mm", "width_mm", "height_mm", "weight_g",
                     "fragile", "this_side_up")
    search_fields = ("sku", "name")
    list_filter = ("fragile", "this_side_up")


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "inner_length_mm", "inner_width_mm", "inner_height_mm",
                     "max_weight_g", "cost", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)
    ordering = ("cost",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    autocomplete_fields = ["product"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reference",)
    inlines = [OrderItemInline]


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("order", "strategy", "primary_box", "total_cost", "utilization", "created_at")
    list_filter = ("strategy",)
    readonly_fields = ("plan", "trace", "created_at")


admin.site.site_header = "Box Selection System"
admin.site.site_title = "Box Selection System"
admin.site.index_title = "Catalogue & Order Administration"
