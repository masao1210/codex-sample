from datetime import date
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from masters.models import Customer, Product
from sales.models import SalesLine, SalesSlip

from . import services
from .models import Invoice, Payment


def make_slip(customer, day, *lines):
    """lines: (単価, 数量, 税率)"""
    slip = SalesSlip.objects.create(customer=customer, date=day)
    for n, (price, qty, rate) in enumerate(lines, start=1):
        SalesLine.objects.create(slip=slip, description=f"品{n}", quantity=qty, unit_price=price, tax_rate=rate, line_no=n)
    slip.recalculate()
    return slip


class CustomerTermsTests(TestCase):
    def test_closing_and_due_dates(self):
        c = Customer(code="X", name="X", closing_day=31, collection_month=1, collection_day=31)
        self.assertEqual(c.closing_date_in(2026, 2), date(2026, 2, 28))
        self.assertEqual(c.due_date_for(date(2026, 1, 31)), date(2026, 2, 28))
        c.closing_day, c.collection_month, c.collection_day = 20, 2, 10
        self.assertEqual(c.closing_date_in(2026, 11), date(2026, 11, 20))
        self.assertEqual(c.due_date_for(date(2026, 11, 20)), date(2027, 1, 10))  # 年をまたぐ


class ClosingTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code="C1", name="株式会社テスト", closing_day=31)
        self.other = Customer.objects.create(code="C2", name="別会社", closing_day=20)

    def test_first_and_second_invoice_carry_balance(self):
        make_slip(self.customer, date(2026, 9, 5), (1000, 3, 10))       # 3,300
        make_slip(self.customer, date(2026, 9, 25), (500, 2, 8))         # 1,080
        make_slip(self.customer, date(2026, 10, 3), (1000, 1, 10))       # 10月分なので入らない
        inv1 = services.create_invoice(self.customer, date(2026, 9, 30))
        self.assertEqual(inv1.number, "B000001")
        self.assertEqual((inv1.previous_amount, inv1.payment_amount, inv1.sales_total, inv1.billed_amount),
                         (0, 0, Decimal(4380), Decimal(4380)))
        self.assertEqual(inv1.sales_slips.count(), 2)
        self.assertEqual(inv1.due_date, date(2026, 10, 31))
        self.assertIsNone(inv1.period_start)

        # 一部入金（振込手数料 440 円を差し引かれた）
        Payment.objects.create(customer=self.customer, date=date(2026, 10, 20), amount=3000, fee=440)
        self.assertEqual(services.outstanding_amount(inv1), Decimal(940))

        inv2 = services.create_invoice(self.customer, date(2026, 10, 31))
        self.assertEqual(inv2.period_start, date(2026, 10, 1))
        self.assertEqual(inv2.previous_amount, Decimal(4380))
        self.assertEqual(inv2.payment_amount, Decimal(3440))
        self.assertEqual(inv2.carried_amount, Decimal(940))
        self.assertEqual(inv2.sales_total, Decimal(1100))
        self.assertEqual(inv2.billed_amount, Decimal(2040))

        balance = services.customers_with_balances().get(pk=self.customer.pk).balance
        self.assertEqual(balance, inv2.billed_amount)

    def test_cannot_close_same_or_earlier_date_twice(self):
        make_slip(self.customer, date(2026, 9, 5), (1000, 1, 10))
        services.create_invoice(self.customer, date(2026, 9, 30))
        make_slip(self.customer, date(2026, 9, 10), (1000, 1, 10))
        with self.assertRaises(services.ClosingError):
            services.create_invoice(self.customer, date(2026, 9, 30))

    def test_late_entered_slip_goes_into_next_invoice(self):
        make_slip(self.customer, date(2026, 9, 5), (1000, 1, 10))
        services.create_invoice(self.customer, date(2026, 9, 30))
        late = make_slip(self.customer, date(2026, 9, 28), (2000, 1, 10))  # 締めた後に9月分を入力
        inv2 = services.create_invoice(self.customer, date(2026, 10, 31))
        late.refresh_from_db()
        self.assertEqual(late.invoice, inv2)

    def test_nothing_to_bill(self):
        with self.assertRaises(services.ClosingError):
            services.create_invoice(self.customer, date(2026, 9, 30))

    def test_drafts_only_for_matching_closing_day(self):
        make_slip(self.customer, date(2026, 9, 5), (1000, 1, 10))
        make_slip(self.other, date(2026, 9, 5), (1000, 1, 10))
        drafts, _ = services.drafts_for_closing(2026, 9, 20)
        self.assertEqual([d.customer for d in drafts], [self.other])
        self.assertEqual(drafts[0].closing_date, date(2026, 9, 20))

    def test_cancel_only_latest_and_releases_items(self):
        s1 = make_slip(self.customer, date(2026, 9, 5), (1000, 1, 10))
        inv1 = services.create_invoice(self.customer, date(2026, 9, 30))
        p = Payment.objects.create(customer=self.customer, date=date(2026, 10, 10), amount=1100)
        inv2 = services.create_invoice(self.customer, date(2026, 10, 31))
        with self.assertRaises(services.ClosingError):
            services.cancel_invoice(inv1)
        services.cancel_invoice(inv2)
        p.refresh_from_db()
        self.assertIsNone(p.invoice)
        services.cancel_invoice(Invoice.objects.get(pk=inv1.pk))
        s1.refresh_from_db()
        self.assertIsNone(s1.invoice)
        self.assertFalse(Invoice.objects.exists())

    def test_tax_breakdown_sums_slip_taxes(self):
        make_slip(self.customer, date(2026, 9, 1), (99, 1, 10))  # 税 9
        make_slip(self.customer, date(2026, 9, 2), (99, 1, 10))  # 税 9
        make_slip(self.customer, date(2026, 9, 3), (1000, 1, 8))  # 税 80
        inv = services.create_invoice(self.customer, date(2026, 9, 30))
        self.assertEqual(
            [(r["rate"], r["subtotal"], r["tax"]) for r in services.invoice_tax_breakdown(inv)],
            [(10, Decimal(198), Decimal(18)), (8, Decimal(1000), Decimal(80))],
        )
        self.assertEqual(inv.sales_tax, Decimal(98))


class BillingViewTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("u", password="pass12345"))
        self.customer = Customer.objects.create(code="C1", name="株式会社テスト", closing_day=31)
        self.product = Product.objects.create(code="P1", name="商品", sale_price=1000)
        self.slip = make_slip(self.customer, date(2026, 9, 5), (1000, 2, 10))

    def test_closing_preview_and_create(self):
        params = {"month": "2026-09", "closing_day": "31", "issue_date": ""}
        resp = self.client.get(reverse("invoices:close"), params)
        self.assertContains(resp, "株式会社テスト")
        self.assertContains(resp, "2,200")
        resp = self.client.post(reverse("invoices:close"), {**params, "customer": [self.customer.pk]})
        self.assertRedirects(resp, reverse("invoices:list") + "?month=2026-09")
        inv = Invoice.objects.get()
        self.assertEqual(inv.issue_date, date(2026, 9, 30))

        detail = self.client.get(inv.get_absolute_url())
        self.assertContains(detail, "今回御請求額")
        self.assertContains(detail, "¥2,200")
        self.assertContains(self.client.get(reverse("invoices:list")), "未入金")

    def test_invoiced_slip_and_payment_are_locked(self):
        Payment.objects.create(customer=self.customer, date=date(2026, 9, 20), amount=500)
        services.create_invoice(self.customer, date(2026, 9, 30))
        payment = Payment.objects.get()
        for url in [reverse("sales:update", args=[self.slip.pk]), reverse("sales:delete", args=[self.slip.pk])]:
            resp = self.client.post(url, {})
            self.assertRedirects(resp, self.slip.get_absolute_url())
        resp = self.client.post(reverse("payments:delete", args=[payment.pk]))
        self.assertRedirects(resp, reverse("payments:list"))
        self.assertTrue(SalesSlip.objects.filter(pk=self.slip.pk).exists())
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())

    def test_cancel_view(self):
        inv = services.create_invoice(self.customer, date(2026, 9, 30))
        resp = self.client.post(reverse("invoices:cancel", args=[inv.pk]))
        self.assertRedirects(resp, reverse("invoices:list"))
        self.slip.refresh_from_db()
        self.assertIsNone(self.slip.invoice)

    def test_payment_create_and_receivables(self):
        resp = self.client.post(reverse("payments:create"), {
            "date": "2026-10-10", "customer": self.customer.pk, "method": "transfer", "amount": "1760", "fee": "440",
        })
        self.assertRedirects(resp, reverse("payments:list"))
        self.assertEqual(Payment.objects.get().number, "R000001")
        resp = self.client.get(reverse("receivables"), {"all": "1"})
        row = next(c for c in resp.context["rows"] if c.pk == self.customer.pk)
        self.assertEqual(row.balance, 0)

    def test_payment_must_be_positive(self):
        resp = self.client.post(reverse("payments:create"), {
            "date": "2026-10-10", "customer": self.customer.pk, "method": "cash", "amount": "0", "fee": "0",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Payment.objects.exists())

    def test_pages_render(self):
        for name in ["invoices:list", "invoices:close", "payments:list", "payments:create", "receivables", "dashboard"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


class DemoDataConsistencyTests(TestCase):
    def test_latest_invoice_matches_balance(self):
        """どの得意先も「最新の請求額 − その後の入金 ＋ 未請求の売上 ＝ 売掛金残高」になっている。"""
        call_command("load_demo", stdout=StringIO())
        self.assertTrue(Invoice.objects.exists())
        for c in services.customers_with_balances():
            inv = services.latest_invoice(c)
            billed = services.outstanding_amount(inv) if inv else -sum(
                (p.applied_amount for p in c.payments.all()), Decimal(0)
            )
            self.assertEqual(billed + c.unbilled_sum, c.balance, c.name)

    def test_demo_data_has_no_overpayments(self):
        call_command("load_demo", stdout=StringIO())
        self.assertFalse(services.customers_with_balances().filter(balance__lt=0).exists())
