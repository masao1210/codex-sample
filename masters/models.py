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


class Customer(PartnerBase):
    class Meta(PartnerBase.Meta):
        verbose_name = verbose_name_plural = "得意先"


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
