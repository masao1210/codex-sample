from django.urls import include, path

from . import views


def crud(ns, list_view, create_view, update_view, delete_view):
    patterns = [
        path("", list_view.as_view(), name="list"),
        path("new/", create_view.as_view(), name="create"),
        path("<int:pk>/", update_view.as_view(), name="update"),
        path("<int:pk>/delete/", delete_view.as_view(), name="delete"),
    ]
    return include((patterns, ns))


urlpatterns = [
    path("customers/", crud("customers", views.CustomerList, views.CustomerCreate, views.CustomerUpdate, views.CustomerDelete)),
    path("suppliers/", crud("suppliers", views.SupplierList, views.SupplierCreate, views.SupplierUpdate, views.SupplierDelete)),
    path("products/", crud("products", views.ProductList, views.ProductCreate, views.ProductUpdate, views.ProductDelete)),
]
