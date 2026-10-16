from django.urls import path

from . import views

app_name = "purchases"

urlpatterns = [
    path("", views.PurchaseList.as_view(), name="list"),
    path("new/", views.PurchaseCreate.as_view(), name="create"),
    path("<int:pk>/", views.PurchaseDetail.as_view(), name="detail"),
    path("<int:pk>/edit/", views.PurchaseUpdate.as_view(), name="update"),
    path("<int:pk>/delete/", views.PurchaseDelete.as_view(), name="delete"),
]
