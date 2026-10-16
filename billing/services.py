"""請求の締め処理と売掛金の計算。

請求書は残高繰越方式で作る。
- 対象の売上: その得意先の、まだどの請求書にも入っていない、締日までの売上伝票
- 対象の入金: その得意先の、まだどの請求書にも入っていない、締日までの入金
  （前回の締日より前の日付でも、あとから入力したものは次の請求書に入る）
- 消費税は売上伝票ごとに計算済みの額を合計する（納品書の税額と請求書の税額が一致する）
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from masters.models import Customer
from sales.models import SalesSlip

from .models import Invoice, Payment

ZERO = Decimal(0)


class ClosingError(Exception):
    pass


@dataclass
class InvoiceDraft:
    """締め処理の下書き（保存前の請求書と、紐づける伝票・入金）。"""

    customer: Customer
    closing_date: object
    previous: Invoice | None
    slips: list = field(default_factory=list)
    payments: list = field(default_factory=list)

    @property
    def period_start(self):
        return self.previous.closing_date + timedelta(days=1) if self.previous else None

    @property
    def due_date(self):
        return self.customer.due_date_for(self.closing_date)

    @property
    def previous_amount(self):
        return self.previous.billed_amount if self.previous else ZERO

    @property
    def payment_amount(self):
        return sum((p.applied_amount for p in self.payments), ZERO)

    @property
    def carried_amount(self):
        return self.previous_amount - self.payment_amount

    @property
    def sales_subtotal(self):
        return sum((s.subtotal for s in self.slips), ZERO)

    @property
    def sales_tax(self):
        return sum((s.tax for s in self.slips), ZERO)

    @property
    def sales_total(self):
        return sum((s.total for s in self.slips), ZERO)

    @property
    def billed_amount(self):
        return self.carried_amount + self.sales_total

    @property
    def is_empty(self):
        """請求するものが何もない（売上も入金もなく、繰越もゼロ）。"""
        return not self.slips and not self.payments and self.carried_amount == 0


def latest_invoice(customer):
    return Invoice.objects.filter(customer=customer).order_by("-closing_date").first()


def draft_invoice(customer, closing_date):
    previous = latest_invoice(customer)
    if previous and previous.closing_date >= closing_date:
        raise ClosingError(f"{previous.closing_date:%Y/%m/%d} 締めの請求書がすでにあります。")
    slips = SalesSlip.objects.filter(customer=customer, invoice__isnull=True, date__lte=closing_date).order_by("date", "number")
    payments = Payment.objects.filter(customer=customer, invoice__isnull=True, date__lte=closing_date).order_by("date", "number")
    return InvoiceDraft(customer, closing_date, previous, list(slips), list(payments))


def drafts_for_closing(year, month, closing_day):
    """指定した締日グループの得意先について、締め処理の下書きを作る。

    戻り値: (下書きのリスト, [(得意先, 作れない理由)])
    """
    drafts, skipped = [], []
    for customer in Customer.objects.filter(closing_day=closing_day):
        try:
            draft = draft_invoice(customer, customer.closing_date_in(year, month))
        except ClosingError as e:
            skipped.append((customer, str(e)))
            continue
        if not draft.is_empty:
            drafts.append(draft)
    return drafts, skipped


@transaction.atomic
def create_invoice(customer, closing_date, issue_date=None):
    draft = draft_invoice(Customer.objects.select_for_update().get(pk=customer.pk), closing_date)
    if draft.is_empty:
        raise ClosingError("請求する売上・入金・繰越残高がありません。")
    invoice = Invoice.objects.create(
        customer=customer,
        closing_date=closing_date,
        period_start=draft.period_start,
        issue_date=issue_date or closing_date,
        due_date=draft.due_date,
        previous_amount=draft.previous_amount,
        payment_amount=draft.payment_amount,
        carried_amount=draft.carried_amount,
        sales_subtotal=draft.sales_subtotal,
        sales_tax=draft.sales_tax,
        sales_total=draft.sales_total,
        billed_amount=draft.billed_amount,
    )
    SalesSlip.objects.filter(pk__in=[s.pk for s in draft.slips]).update(invoice=invoice)
    Payment.objects.filter(pk__in=[p.pk for p in draft.payments]).update(invoice=invoice)
    return invoice


@transaction.atomic
def cancel_invoice(invoice):
    """請求書を取り消し、紐づいていた売上伝票と入金を未請求に戻す。最新の請求書だけ取り消せる。"""
    if not invoice.is_latest:
        raise ClosingError("この得意先には後の請求書があるため取り消せません。新しい請求書から順に取り消してください。")
    invoice.sales_slips.update(invoice=None)
    invoice.payments.update(invoice=None)
    invoice.delete()


def invoice_tax_breakdown(invoice):
    """請求書の税率ごとの内訳。各伝票で計算済みの税額を税率ごとに合計する。"""
    totals = defaultdict(lambda: {"subtotal": ZERO, "tax": ZERO})
    for slip in invoice.sales_slips.prefetch_related("lines"):
        for r in slip.tax_summary()["by_rate"]:
            totals[r["rate"]]["subtotal"] += r["subtotal"]
            totals[r["rate"]]["tax"] += r["tax"]
    return [{"rate": rate, **totals[rate]} for rate in sorted(totals, reverse=True)]


def outstanding_amount(invoice):
    """最新の請求書について、まだ入金されていない額（その後の未請求の入金を差し引く）。"""
    paid = Payment.objects.filter(customer=invoice.customer_id, invoice__isnull=True).aggregate(
        s=Sum(F("amount") + F("fee"))
    )["s"] or ZERO
    return invoice.billed_amount - paid


def _sum_subquery(qs, expr):
    money = DecimalField(max_digits=14, decimal_places=0)
    sub = qs.filter(customer=OuterRef("pk")).values("customer").annotate(s=Sum(expr)).values("s")
    return Coalesce(Subquery(sub, output_field=money), Value(ZERO), output_field=money)


def customers_with_balances():
    """得意先ごとの売上累計・入金累計・売掛金残高・未請求売上を付けた QuerySet。"""
    return Customer.objects.annotate(
        sales_sum=_sum_subquery(SalesSlip.objects.all(), "total"),
        paid_sum=_sum_subquery(Payment.objects.all(), F("amount") + F("fee")),
        unbilled_sum=_sum_subquery(SalesSlip.objects.filter(invoice__isnull=True), "total"),
    ).annotate(balance=F("sales_sum") - F("paid_sum"))
