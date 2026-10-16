import calendar
from datetime import date

from django.db import models

from core.tax import TaxRate


class PartnerBase(models.Model):
    """得意先・仕入先の共通項目。"""

    code = models.CharField("コード", max_length=20, unique=True)
    name = models.CharField("名称", max_length=100)
    kana = models.CharField("フリガナ", max_length=100, blank=True)
    honorific = models.CharField("敬称", max_length=10, default="御中", blank=True)
    postal_code = models.CharField("郵便番号", max_length=10, blank=True)
    address = models.CharField("住所", max_length=200, blank=True)
    phone = models.CharField("電話番号", max_length=20, blank=True)
    email = models.EmailField("メール", blank=True)
    notes = models.TextField("備考", blank=True)
    is_active = models.BooleanField("有効", default=True)

    class Meta:
        abstract = True
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


END_OF_MONTH = 31
DAY_CHOICES = [(d, f"{d}日") for d in range(1, 29)] + [(END_OF_MONTH, "末日")]


class Customer(PartnerBase):
    closing_day = models.PositiveSmallIntegerField("締日", choices=DAY_CHOICES, default=END_OF_MONTH)
    collection_month = models.PositiveSmallIntegerField(
        "回収月", choices=[(0, "当月"), (1, "翌月"), (2, "翌々月"), (3, "3か月後")], default=1
    )
    collection_day = models.PositiveSmallIntegerField("回収日", choices=DAY_CHOICES, default=END_OF_MONTH)

    class Meta(PartnerBase.Meta):
        verbose_name = verbose_name_plural = "得意先"

    @property
    def terms_display(self):
        return f"{self.get_closing_day_display()}締め {self.get_collection_month_display()}{self.get_collection_day_display()}回収"

    def closing_date_in(self, year, month):
        """指定した年月の締日。"""
        return day_in_month(year, month, self.closing_day)

    def due_date_for(self, closing_date):
        """締日に対する回収予定日。"""
        y, m = divmod(closing_date.month - 1 + self.collection_month, 12)
        return day_in_month(closing_date.year + y, m + 1, self.collection_day)


class Supplier(PartnerBase):
    invoice_number = models.CharField("登録番号（T+13桁）", max_length=14, blank=True)

    class Meta(PartnerBase.Meta):
        verbose_name = verbose_name_plural = "仕入先"


class Product(models.Model):
    code = models.CharField("コード", max_length=30, unique=True)
    name = models.CharField("商品名", max_length=200)
    unit = models.CharField("単位", max_length=20, default="個", blank=True)
    sale_price = models.DecimalField("標準売価（税抜）", max_digits=14, decimal_places=2, default=0)
    purchase_price = models.DecimalField("標準仕入単価（税抜）", max_digits=14, decimal_places=2, default=0)
    tax_rate = models.PositiveSmallIntegerField("税率", choices=TaxRate.choices, default=TaxRate.STANDARD)
    notes = models.TextField("備考", blank=True)
    is_active = models.BooleanField("有効", default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = verbose_name_plural = "商品"

    def __str__(self):
        return f"{self.code} {self.name}"


def day_in_month(year, month, day):
    """year 年 month 月の day 日。月の日数を超える日（末日=31 など）はその月の末日にする。"""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))
