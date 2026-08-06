from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from warehouse.models import Box, Order, Product, Recommendation
from warehouse.services import cart_lines_to_domain_items, recommend, recommend_for_order

from .serializers import (
    BoxSerializer,
    OrderSerializer,
    ProductSerializer,
    RecommendationSerializer,
    RecommendRequestSerializer,
)


class HealthView(APIView):
    """Liveness check — used by Docker healthchecks and CI smoke tests."""

    def get(self, request):
        return Response({"status": "ok"})


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["fragile", "this_side_up"]
    lookup_field = "sku"


class BoxViewSet(viewsets.ModelViewSet):
    queryset = Box.objects.all()
    serializer_class = BoxSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_active"]
    lookup_field = "code"


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related("items__product")
    serializer_class = OrderSerializer

    @extend_schema(
        summary="Compute and persist a box recommendation for this order",
        responses={200: RecommendationSerializer},
    )
    @action(detail=True, methods=["post"])
    def recommend(self, request, pk=None):
        order = self.get_object()
        if not order.items.exists():
            return Response(
                {"detail": "Order has no items to recommend a box for."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        allow_multi_box = request.data.get("allow_multi_box", True)
        recommendation = recommend_for_order(order, allow_multi_box=allow_multi_box)
        return Response(RecommendationSerializer(recommendation).data)

    @extend_schema(
        summary="Fetch the most recently computed recommendation for this order",
        responses={200: RecommendationSerializer},
    )
    @action(detail=True, methods=["get"], url_path="recommendation")
    def get_recommendation(self, request, pk=None):
        order = self.get_object()
        recommendation = get_object_or_404(Recommendation, order=order)
        return Response(RecommendationSerializer(recommendation).data)


class RecommendView(APIView):
    """
    Stateless box recommendation: given a cart of SKUs and quantities,
    return the cheapest box that fits, WITHOUT requiring a saved Order.

    Every box in the active catalogue is evaluated; the response
    includes a verdict + human-readable reason for every one of them,
    not just the winner (`evaluated`).
    """

    @extend_schema(
        request=RecommendRequestSerializer,
        examples=[
            OpenApiExample(
                "Mug + book",
                value={"items": [{"sku": "MUG-001", "quantity": 1}, {"sku": "BOOK-001", "quantity": 1}]},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = RecommendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            items = cart_lines_to_domain_items(data["items"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        allow_multi_box = data.get("options", {}).get("allow_multi_box", True)
        result = recommend(items, allow_multi_box=allow_multi_box)

        return Response(
            {
                "strategy": result.strategy,
                "recommended_box": (
                    BoxSerializer(result.recommended_box).data if result.recommended_box else None
                ),
                "total_cost": str(result.total_cost) if result.total_cost is not None else None,
                "utilization": result.utilization,
                "plan": result.plan,
                "evaluated": result.trace,
            }
        )
