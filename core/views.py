from datetime import date

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from purchases.models import PurchaseSlip
from sales.models import SalesSlip


def _months_back(today, n):
    """today を含む直近 n か月の各月初日（古い順）。"""
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append(date(y, m, 1))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return list(reversed(months))


def _monthly_totals(model, since):
    rows = (
        model.objects.filter(date__gte=since)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("subtotal"))
    )
    return {r["month"]: r["total"] for r in rows}


def dashboard(request):
    today = timezone.localdate()
    months = _months_back(today, 12)
    sales = _monthly_totals(SalesSlip, months[0])
    purchases = _monthly_totals(PurchaseSlip, months[0])

    monthly = []
    for m in months:
        s, p = sales.get(m) or 0, purchases.get(m) or 0
        monthly.append({"month": m, "sales": s, "purchases": p, "diff": s - p})
    monthly.reverse()

    return render(
        request,
        "core/dashboard.html",
        {
            "this_month": monthly[0],
            "monthly": monthly,
            "recent_sales": SalesSlip.objects.select_related("customer")[:5],
            "recent_purchases": PurchaseSlip.objects.select_related("supplier")[:5],
        },
    )
