"""お試し用のサンプルデータを登録する: python manage.py load_demo"""

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from masters.models import Customer, Product, Supplier
from purchases.models import PurchaseLine, PurchaseSlip
from sales.models import SalesLine, SalesSlip


class Command(BaseCommand):
    help = "お試し用のサンプルデータ（得意先・仕入先・商品・伝票）を登録します。"

    @transaction.atomic
    def handle(self, *args, **options):
        if Customer.objects.exists() or Product.objects.exists():
            self.stdout.write(self.style.WARNING("すでにデータがあるため、サンプルデータは登録しませんでした。"))
            return

        customers = [
            Customer.objects.create(code="C001", name="株式会社あおば商事", kana="アオバショウジ", postal_code="100-0001", address="東京都千代田区千代田1-1", phone="03-0000-0001"),
            Customer.objects.create(code="C002", name="みどり食品株式会社", kana="ミドリショクヒン", address="大阪府大阪市北区1-2-3", phone="06-0000-0002"),
        ]
        supplier = Supplier.objects.create(code="V001", name="有限会社やまと卸", kana="ヤマトオロシ", invoice_number="T1234567890123")
        products = [
            Product.objects.create(code="F001", name="国産りんご 10kg", unit="箱", sale_price=Decimal("4800"), purchase_price=Decimal("3200"), tax_rate=8),
            Product.objects.create(code="F002", name="緑茶ティーバッグ 100袋", unit="袋", sale_price=Decimal("980"), purchase_price=Decimal("600"), tax_rate=8),
            Product.objects.create(code="G001", name="コピー用紙 A4 500枚", unit="冊", sale_price=Decimal("550"), purchase_price=Decimal("380")),
            Product.objects.create(code="G002", name="ボールペン 黒", unit="本", sale_price=Decimal("120"), purchase_price=Decimal("70")),
        ]

        today = timezone.localdate()
        for i in range(8):
            day = today - timedelta(days=i * 20)
            slip = SalesSlip.objects.create(customer=customers[i % 2], date=day)
            for n, (p, qty) in enumerate([(products[i % 4], 2 + i), (products[(i + 1) % 4], 5)], start=1):
                SalesLine.objects.create(slip=slip, product=p, description=p.name, quantity=qty, unit=p.unit,
                                         unit_price=p.sale_price, tax_rate=p.tax_rate, line_no=n)
            slip.recalculate()

            pslip = PurchaseSlip.objects.create(supplier=supplier, date=day - timedelta(days=3))
            p = products[i % 4]
            PurchaseLine.objects.create(slip=pslip, product=p, description=p.name, quantity=10, unit=p.unit,
                                        unit_price=p.purchase_price, tax_rate=p.tax_rate, line_no=1)
            pslip.recalculate()

        self.stdout.write(self.style.SUCCESS("サンプルデータを登録しました。"))
