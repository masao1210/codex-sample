from django.contrib import admin

from .models import Customer, Product, Supplier


@admin.register(Customer, Supplier)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "phone", "is_active")
    search_fields = ("code", "name", "kana")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "sale_price", "purchase_price", "tax_rate", "is_active")
    search_fields = ("code", "name")
