from django.contrib import admin

from .models import SalesLine, SalesSlip


class LineInline(admin.TabularInline):
    model = SalesLine
    extra = 0


@admin.register(SalesSlip)
class SlipAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "customer", "total")
    search_fields = ("number", "customer__name")
    inlines = [LineInline]
    readonly_fields = ("subtotal", "tax", "total")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalculate()
