from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("", views.SalesList.as_view(), name="list"),
    path("new/", views.SalesCreate.as_view(), name="create"),
    path("<int:pk>/", views.SalesDetail.as_view(), name="detail"),
    path("<int:pk>/edit/", views.SalesUpdate.as_view(), name="update"),
    path("<int:pk>/delete/", views.SalesDelete.as_view(), name="delete"),
]
