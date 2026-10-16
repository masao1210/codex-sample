from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import dashboard

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("masters/", include("masters.urls")),
    path("sales/", include("sales.urls")),
    path("purchases/", include("purchases.urls")),
    path("billing/", include("billing.urls")),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
]
