from django.contrib import admin

from .models import Invoice, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """請求書は締め処理で作るため、管理画面では見るだけにする。"""

    list_display = ("number", "closing_date", "customer", "billed_amount", "due_date")
    search_fields = ("number", "customer__name")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "customer", "amount", "fee", "invoice")
    search_fields = ("number", "customer__name")

    def has_change_permission(self, request, obj=None):
        return obj is None or not obj.is_locked

    def has_delete_permission(self, request, obj=None):
        return obj is None or not obj.is_locked
