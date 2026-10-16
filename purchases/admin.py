from django.contrib import admin

from .models import PurchaseLine, PurchaseSlip


class LineInline(admin.TabularInline):
    model = PurchaseLine
    extra = 0


@admin.register(PurchaseSlip)
class SlipAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "supplier", "total")
    search_fields = ("number", "supplier__name")
    inlines = [LineInline]
    readonly_fields = ("subtotal", "tax", "total")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalculate()
