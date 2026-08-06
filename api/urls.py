from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="product")
router.register("boxes", views.BoxViewSet, basename="box")
router.register("orders", views.OrderViewSet, basename="order")

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    path("recommend/", views.RecommendView.as_view(), name="recommend"),
    path("", include(router.urls)),
]
