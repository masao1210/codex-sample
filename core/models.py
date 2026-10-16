"""売上伝票・仕入伝票などで共通に使う抽象モデル。"""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from core import tax


class NumberedModel(models.Model):
    """「S000001」のような連番を自動で振るモデル。子クラスは NUMBER_PREFIX を指定する。"""

    NUMBER_PREFIX = ""

    number = models.CharField("番号", max_length=20, unique=True, editable=False)

    class Meta:
        abstract = True

    def __str__(self):
        return self.number

    @classmethod
    def next_number(cls):
        last = (
            cls.objects.filter(number__startswith=cls.NUMBER_PREFIX)
            .order_by("-number")
            .values_list("number", flat=True)
            .first()
        )
        seq = int(last[len(cls.NUMBER_PREFIX):]) + 1 if last else 1
        return f"{cls.NUMBER_PREFIX}{seq:06d}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.next_number()
        super().save(*args, **kwargs)


class SlipBase(NumberedModel):
    """伝票ヘッダの共通部分。子クラスは NUMBER_PREFIX と lines（明細の related_name）を持つ。"""

    number = models.CharField("伝票番号", max_length=20, unique=True, editable=False)
    date = models.DateField("日付", default=timezone.localdate)
    notes = models.TextField("備考", blank=True)
    subtotal = models.DecimalField("税抜金額", max_digits=14, decimal_places=0, default=0, editable=False)
    tax = models.DecimalField("消費税", max_digits=14, decimal_places=0, default=0, editable=False)
    total = models.DecimalField("合計金額", max_digits=14, decimal_places=0, default=0, editable=False)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-date", "-number"]

    def tax_summary(self):
        return tax.summarize((line.tax_rate, line.amount) for line in self.lines.all())

    def recalculate(self):
        """明細から金額を計算し直して保存する。明細を保存した後に呼ぶ。"""
        summary = self.tax_summary()
        self.subtotal = summary["subtotal"]
        self.tax = summary["tax"]
        self.total = summary["total"]
        self.save(update_fields=["subtotal", "tax", "total", "updated_at"])


class SlipLineBase(models.Model):
    """伝票明細の共通部分。子クラスは slip（親伝票への FK）と product を持つ。"""

    description = models.CharField("品名", max_length=200)
    quantity = models.DecimalField("数量", max_digits=12, decimal_places=2, default=Decimal("1"))
    unit = models.CharField("単位", max_length=20, blank=True)
    unit_price = models.DecimalField("単価", max_digits=14, decimal_places=2)
    tax_rate = models.PositiveSmallIntegerField("税率", choices=tax.TaxRate.choices, default=tax.TaxRate.STANDARD)
    amount = models.DecimalField("金額", max_digits=14, decimal_places=0, default=0, editable=False)
    line_no = models.PositiveIntegerField("行", default=0)

    class Meta:
        abstract = True
        ordering = ["line_no", "id"]

    def __str__(self):
        return self.description

    def save(self, *args, **kwargs):
        self.amount = tax.line_amount(self.quantity, self.unit_price)
        super().save(*args, **kwargs)
