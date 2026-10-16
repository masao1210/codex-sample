from django.urls import include, path

from . import views

invoice_patterns = [
    path("", views.InvoiceList.as_view(), name="list"),
    path("close/", views.InvoiceClose.as_view(), name="close"),
    path("<int:pk>/", views.InvoiceDetail.as_view(), name="detail"),
    path("<int:pk>/cancel/", views.InvoiceCancel.as_view(), name="cancel"),
]

payment_patterns = [
    path("", views.PaymentList.as_view(), name="list"),
    path("new/", views.PaymentCreate.as_view(), name="create"),
    path("<int:pk>/", views.PaymentUpdate.as_view(), name="update"),
    path("<int:pk>/delete/", views.PaymentDelete.as_view(), name="delete"),
]

urlpatterns = [
    path("invoices/", include((invoice_patterns, "invoices"))),
    path("payments/", include((payment_patterns, "payments"))),
    path("receivables/", views.receivables, name="receivables"),
]
