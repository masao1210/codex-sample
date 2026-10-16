from django.db import models
from django.urls import reverse

from core.models import SlipBase, SlipLineBase
from masters.models import Product, Supplier


class PurchaseSlip(SlipBase):
    NUMBER_PREFIX = "P"

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_slips", verbose_name="仕入先")
    supplier_ref = models.CharField("先方伝票番号", max_length=50, blank=True)

    class Meta(SlipBase.Meta):
        verbose_name = verbose_name_plural = "仕入伝票"

    def get_absolute_url(self):
        return reverse("purchases:detail", args=[self.pk])


class PurchaseLine(SlipLineBase):
    slip = models.ForeignKey(PurchaseSlip, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True, verbose_name="商品")

    class Meta(SlipLineBase.Meta):
        verbose_name = verbose_name_plural = "仕入明細"
