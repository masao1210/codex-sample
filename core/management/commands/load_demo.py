"""お試し用のサンプルデータを登録する: python manage.py load_demo"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from billing.models import Payment
from billing.services import create_invoice, drafts_for_closing, outstanding_amount
from core.demo_data import SEED, dummy_customers, dummy_products
from masters.models import Customer, Product, Supplier
from purchases.models import PurchaseLine, PurchaseSlip
from sales.models import SalesLine, SalesSlip


class Command(BaseCommand):
    help = (
        "お試し用のサンプルデータ（得意先・商品は各100件、仕入先、伝票、請求書、入金）を登録します。"
        "同じコードのマスタがすでにあればそのまま残し、伝票は1件もないときだけ作ります。"
    )

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=100, help="得意先の件数（既定: 100）")
        parser.add_argument("--products", type=int, default=100, help="商品の件数（既定: 100、最大100）")

    @transaction.atomic
    def handle(self, *args, **options):
        new_customers = sum(
            Customer.objects.get_or_create(code=row.pop("code"), defaults=row)[1]
            for row in dummy_customers(options["customers"])
        )
        new_products = sum(
            Product.objects.get_or_create(code=row.pop("code"), defaults=row)[1]
            for row in dummy_products(options["products"])
        )
        supplier, _ = Supplier.objects.get_or_create(
            code="V001", defaults={"name": "有限会社やまと卸", "kana": "ヤマトオロシ", "invoice_number": "T1234567890123"}
        )
        self.stdout.write(f"得意先を {new_customers} 件、商品を {new_products} 件追加しました。")

        if SalesSlip.objects.exists() or PurchaseSlip.objects.exists():
            self.stdout.write("伝票がすでにあるため、サンプル伝票は作りませんでした。")
            return

        rng = random.Random(SEED)
        customers = list(Customer.objects.filter(is_active=True))
        products = list(Product.objects.filter(is_active=True))
        today = timezone.localdate()
        for i in range(24):
            day = today - timedelta(days=i * 15)
            slip = SalesSlip.objects.create(customer=rng.choice(customers), date=day)
            for n, p in enumerate(rng.sample(products, rng.randint(1, 4)), start=1):
                SalesLine.objects.create(slip=slip, product=p, description=p.name, quantity=rng.randint(1, 20),
                                         unit=p.unit, unit_price=p.sale_price, tax_rate=p.tax_rate, line_no=n)
            slip.recalculate()

            if i % 2 == 0:
                pslip = PurchaseSlip.objects.create(supplier=supplier, date=day - timedelta(days=3))
                for n, p in enumerate(rng.sample(products, rng.randint(1, 3)), start=1):
                    PurchaseLine.objects.create(slip=pslip, product=p, description=p.name, quantity=rng.randint(10, 50),
                                                unit=p.unit, unit_price=p.purchase_price, tax_rate=p.tax_rate, line_no=n)
                pslip.recalculate()

        invoices, payments = self._create_invoices_and_payments(rng, today)
        self.stdout.write(self.style.SUCCESS(
            f"サンプル伝票（売上24件・仕入12件）、請求書 {invoices} 件、入金 {payments} 件を作りました。"
        ))

    def _create_invoices_and_payments(self, rng, today):
        """過去6か月を月ごとに締め、入金予定日を過ぎた請求はおおむね入金済みにする。"""
        invoices = payments = 0
        closing_days = sorted(set(Customer.objects.values_list("closing_day", flat=True)))
        for back in range(6, 0, -1):
            y, m = divmod(today.year * 12 + today.month - 1 - back, 12)
            for day in closing_days:
                drafts, _ = drafts_for_closing(y, m + 1, day)
                for draft in drafts:
                    invoice = create_invoice(draft.customer, draft.closing_date)
                    invoices += 1
                    unpaid = outstanding_amount(invoice)
                    if invoice.due_date < today and unpaid > 440 and rng.random() < 0.85:
                        fee = Decimal(440) if rng.random() < 0.3 else Decimal(0)
                        Payment.objects.create(customer=invoice.customer, date=invoice.due_date,
                                               amount=unpaid - fee, fee=fee)
                        payments += 1
        return invoices, payments
