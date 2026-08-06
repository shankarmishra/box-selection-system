from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.HomeView.as_view(), name="home"),
    path("visualize/<int:order_id>/", web_views.VisualizeOrderView.as_view(), name="visualize"),
]
