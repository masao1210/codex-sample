from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.models import NumberedModel
from masters.models import Customer


class Invoice(NumberedModel):
    """請求書（残高繰越方式）。

    今回御請求額 = 前回御請求額 − 今回御入金額 ＋ 今回御買上額（税込）
    締め処理で作り、その期間の売上伝票と入金をこの請求書に紐づける。
    """

    NUMBER_PREFIX = "B"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="invoices", verbose_name="得意先")
    closing_date = models.DateField("締日")
    period_start = models.DateField("対象期間の開始日", null=True, blank=True)
    issue_date = models.DateField("請求日")
    due_date = models.DateField("入金予定日")
    previous_amount = models.DecimalField("前回御請求額", max_digits=14, decimal_places=0, default=0)
    payment_amount = models.DecimalField("今回御入金額", max_digits=14, decimal_places=0, default=0)
    carried_amount = models.DecimalField("繰越金額", max_digits=14, decimal_places=0, default=0)
    sales_subtotal = models.DecimalField("今回御買上額（税抜）", max_digits=14, decimal_places=0, default=0)
    sales_tax = models.DecimalField("消費税額", max_digits=14, decimal_places=0, default=0)
    sales_total = models.DecimalField("今回御買上額（税込）", max_digits=14, decimal_places=0, default=0)
    billed_amount = models.DecimalField("今回御請求額", max_digits=14, decimal_places=0, default=0)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        ordering = ["-closing_date", "-number"]
        verbose_name = verbose_name_plural = "請求書"
        constraints = [models.UniqueConstraint(fields=["customer", "closing_date"], name="unique_invoice_per_closing")]

    def get_absolute_url(self):
        return reverse("invoices:detail", args=[self.pk])

    @property
    def is_latest(self):
        return not Invoice.objects.filter(customer=self.customer_id, closing_date__gt=self.closing_date).exists()


class Payment(NumberedModel):
    """入金。締め処理で請求書に紐づくと、その請求書を取り消すまで編集できない。"""

    NUMBER_PREFIX = "R"

    class Method(models.TextChoices):
        TRANSFER = "transfer", "振込"
        CASH = "cash", "現金"
        BILL = "bill", "手形"
        OFFSET = "offset", "相殺"
        OTHER = "other", "その他"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="payments", verbose_name="得意先")
    date = models.DateField("入金日", default=timezone.localdate)
    method = models.CharField("入金方法", max_length=20, choices=Method.choices, default=Method.TRANSFER)
    amount = models.DecimalField("入金額", max_digits=14, decimal_places=0)
    fee = models.DecimalField(
        "手数料・値引", max_digits=14, decimal_places=0, default=0,
        help_text="先方負担の振込手数料などを差し引かれた場合に入力します。入金額と合わせて売掛金から減らします。",
    )
    notes = models.CharField("備考", max_length=200, blank=True)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments",
        editable=False, verbose_name="請求書",
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        ordering = ["-date", "-number"]
        verbose_name = verbose_name_plural = "入金"

    def get_absolute_url(self):
        return reverse("payments:list")

    @property
    def is_locked(self):
        return self.invoice_id is not None

    @property
    def applied_amount(self):
        """売掛金から減らす額（入金額＋手数料・値引）。"""
        return self.amount + self.fee
