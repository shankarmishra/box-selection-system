from rest_framework import serializers

from warehouse.models import Box, Order, OrderItem, Product, Recommendation


class ProductSerializer(serializers.ModelSerializer):
    volume_mm3 = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "length_mm", "width_mm", "height_mm", "weight_g",
            "fragile", "this_side_up", "volume_mm3",
        ]


class BoxSerializer(serializers.ModelSerializer):
    volume_mm3 = serializers.ReadOnlyField()

    class Meta:
        model = Box
        fields = [
            "id", "code", "name", "inner_length_mm", "inner_width_mm", "inner_height_mm",
            "max_weight_g", "cost", "is_active", "volume_mm3",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_sku", "quantity"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "reference", "status", "created_at", "items"]
        read_only_fields = ["status", "created_at"]


class RecommendationSerializer(serializers.ModelSerializer):
    order_reference = serializers.CharField(source="order.reference", read_only=True)

    class Meta:
        model = Recommendation
        fields = [
            "id", "order", "order_reference", "strategy", "primary_box", "total_cost",
            "utilization", "plan", "trace", "algorithm_version", "created_at",
        ]


# --- request/response shapes for the stateless recommend endpoint ---


class CartLineSerializer(serializers.Serializer):
    sku = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class RecommendOptionsSerializer(serializers.Serializer):
    allow_multi_box = serializers.BooleanField(default=True)


class RecommendRequestSerializer(serializers.Serializer):
    items = CartLineSerializer(many=True)
    options = RecommendOptionsSerializer(required=False, default=dict)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("`items` must contain at least one line.")
        return value
