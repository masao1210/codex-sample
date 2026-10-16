from django.contrib import messages
from django.db.models import F, Max, OuterRef, Q, Subquery, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View, generic

from core.slip_views import LockedObjectMixin
from masters.models import Customer

from . import services
from .forms import ClosingForm, PaymentForm
from .models import Invoice, Payment


class InvoiceList(generic.ListView):
    model = Invoice
    template_name = "billing/invoice_list.html"
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related("customer")
        params = self.request.GET
        if month := params.get("month"):
            try:
                y, m = map(int, month.split("-"))
                qs = qs.filter(closing_date__year=y, closing_date__month=m)
            except ValueError:
                pass
        if customer := params.get("customer", "").strip():
            qs = qs.filter(Q(customer__name__icontains=customer) | Q(customer__code__icontains=customer))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoices = ctx["object_list"]
        customer_ids = {inv.customer_id for inv in invoices}
        latest = dict(
            Invoice.objects.filter(customer__in=customer_ids)
            .values("customer").annotate(d=Max("closing_date")).values_list("customer", "d")
        )
        unbilled_paid = dict(
            Payment.objects.filter(customer__in=customer_ids, invoice__isnull=True)
            .values("customer").annotate(s=Sum(F("amount") + F("fee"))).values_list("customer", "s")
        )
        today = timezone.localdate()
        rows = []
        for inv in invoices:
            row = {"invoice": inv, "is_latest": latest.get(inv.customer_id) == inv.closing_date}
            if row["is_latest"]:
                row["outstanding"] = inv.billed_amount - (unbilled_paid.get(inv.customer_id) or 0)
                row["overdue"] = row["outstanding"] > 0 and inv.due_date < today
            rows.append(row)
        ctx["rows"] = rows
        return ctx


class InvoiceClose(View):
    """請求の締め処理。締日グループと年月を選んで対象を確認し、選んだ得意先の請求書を作る。"""

    template_name = "billing/invoice_close.html"

    def get(self, request):
        form = ClosingForm(request.GET or None)
        ctx = {"form": form}
        if form.is_valid():
            ctx.update(self._preview(form))
        return render(request, self.template_name, ctx)

    def _preview(self, form):
        y, m = form.year_month
        drafts, skipped = services.drafts_for_closing(y, m, form.cleaned_data["closing_day"])
        return {"drafts": drafts, "skipped": skipped, "totals": {
            "billed": sum(d.billed_amount for d in drafts),
            "sales": sum(d.sales_total for d in drafts),
        }}

    def post(self, request):
        form = ClosingForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})
        y, m = form.year_month
        issue_date = form.cleaned_data["issue_date"]
        ids = request.POST.getlist("customer")
        created, errors = [], []
        for customer in Customer.objects.filter(pk__in=ids, closing_day=form.cleaned_data["closing_day"]):
            try:
                created.append(services.create_invoice(customer, customer.closing_date_in(y, m), issue_date))
            except services.ClosingError as e:
                errors.append(f"{customer.name}: {e}")
        if created:
            messages.success(request, f"請求書を {len(created)} 件作成しました。")
        for e in errors:
            messages.error(request, e)
        if not created and not errors:
            messages.error(request, "請求書を作る得意先を選んでください。")
            return redirect(f"{reverse('invoices:close')}?{request.POST.urlencode()}")
        return redirect(f"{reverse('invoices:list')}?month={y:04d}-{m:02d}")


class InvoiceDetail(generic.DetailView):
    model = Invoice
    template_name = "billing/invoice_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        inv = self.object
        ctx["slips"] = inv.sales_slips.order_by("date", "number").prefetch_related("lines")
        ctx["payments"] = inv.payments.order_by("date", "number")
        ctx["tax_breakdown"] = services.invoice_tax_breakdown(inv)
        ctx["is_latest"] = inv.is_latest
        if ctx["is_latest"]:
            ctx["outstanding"] = services.outstanding_amount(inv)
        return ctx


class InvoiceCancel(View):
    template_name = "billing/invoice_cancel.html"

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        return render(request, self.template_name, {"object": invoice, "is_latest": invoice.is_latest})

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        try:
            services.cancel_invoice(invoice)
        except services.ClosingError as e:
            messages.error(request, str(e))
            return redirect(invoice.get_absolute_url())
        messages.success(request, f"請求書 {invoice.number} を取り消しました。売上伝票と入金は未請求に戻りました。")
        return redirect("invoices:list")


class PaymentList(generic.ListView):
    model = Payment
    template_name = "billing/payment_list.html"
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related("customer", "invoice")
        params = self.request.GET
        if date_from := parse_date(params.get("date_from", "")):
            qs = qs.filter(date__gte=date_from)
        if date_to := parse_date(params.get("date_to", "")):
            qs = qs.filter(date__lte=date_to)
        if customer := params.get("customer", "").strip():
            qs = qs.filter(Q(customer__name__icontains=customer) | Q(customer__code__icontains=customer))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["totals"] = self.object_list.aggregate(amount=Sum("amount"), fee=Sum("fee"))
        return ctx


class PaymentFormMixin:
    model = Payment
    form_class = PaymentForm
    template_name = "billing/payment_form.html"
    success_url = reverse_lazy("payments:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["balances"] = {
            c.pk: str(c.balance) for c in services.customers_with_balances().filter(is_active=True)
        }
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"入金 {self.object.number} を保存しました。")
        return response


class PaymentCreate(PaymentFormMixin, generic.CreateView):
    def get_initial(self):
        initial = super().get_initial()
        if customer := self.request.GET.get("customer"):
            initial["customer"] = customer
        return initial


class PaymentUpdate(LockedObjectMixin, PaymentFormMixin, generic.UpdateView):
    pass


class PaymentDelete(LockedObjectMixin, generic.DeleteView):
    model = Payment
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("payments:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "入金"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"入金 {self.object.number} を削除しました。")
        return super().form_valid(form)


def receivables(request):
    """売掛金残高一覧。"""
    latest = Invoice.objects.filter(customer=OuterRef("pk")).order_by("-closing_date")
    qs = services.customers_with_balances().annotate(
        last_closing=Subquery(latest.values("closing_date")[:1]),
        last_due=Subquery(latest.values("due_date")[:1]),
        last_invoice_id=Subquery(latest.values("pk")[:1]),
    ).annotate(billed_unpaid=F("balance") - F("unbilled_sum"))

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(kana__icontains=q))
    if not request.GET.get("all"):
        qs = qs.exclude(balance=0, unbilled_sum=0)

    rows = list(qs)
    today = timezone.localdate()
    for c in rows:
        c.overdue = c.billed_unpaid > 0 and c.last_due is not None and c.last_due < today
    totals = {
        "balance": sum(c.balance for c in rows),
        "unbilled": sum(c.unbilled_sum for c in rows),
        "billed_unpaid": sum(c.billed_unpaid for c in rows),
    }
    return render(request, "billing/receivables.html", {"rows": rows, "totals": totals, "today": today})
