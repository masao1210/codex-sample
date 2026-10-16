from django.db import models
from django.urls import reverse

from core.models import SlipBase, SlipLineBase
from masters.models import Customer, Product


class SalesSlip(SlipBase):
    NUMBER_PREFIX = "S"

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sales_slips", verbose_name="得意先")

    class Meta(SlipBase.Meta):
        verbose_name = verbose_name_plural = "売上伝票"

    def get_absolute_url(self):
        return reverse("sales:detail", args=[self.pk])


class SalesLine(SlipLineBase):
    slip = models.ForeignKey(SalesSlip, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True, verbose_name="商品")

    class Meta(SlipLineBase.Meta):
        verbose_name = verbose_name_plural = "売上明細"
