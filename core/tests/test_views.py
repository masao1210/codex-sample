from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from masters.models import Customer, Product, Supplier
from purchases.models import PurchaseSlip
from sales.models import SalesSlip


def line_data(prefix, rows, initial=0):
    data = {
        f"{prefix}-TOTAL_FORMS": str(len(rows)),
        f"{prefix}-INITIAL_FORMS": str(initial),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    for i, row in enumerate(rows):
        for k, v in row.items():
            data[f"{prefix}-{i}-{k}"] = v
    return data


class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tanaka", password="pass12345")
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(code="C001", name="株式会社サンプル")
        self.supplier = Supplier.objects.create(code="V001", name="有限会社仕入")
        self.apple = Product.objects.create(
            code="P001", name="りんご", unit="箱", sale_price=Decimal("1200"), purchase_price=Decimal("800"), tax_rate=8
        )
        self.pen = Product.objects.create(code="P002", name="ボールペン", sale_price=Decimal("150"), purchase_price=100)

    def test_login_required(self):
        self.client.logout()
        resp = self.client.get(reverse("sales:list"))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('sales:list')}")

    def test_pages_render(self):
        for name in ["dashboard", "sales:list", "sales:create", "purchases:list", "purchases:create",
                     "customers:list", "customers:create", "suppliers:list", "products:list", "products:create"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def create_sales_slip(self, date="2026-10-01"):
        data = {"date": date, "customer": self.customer.pk, "notes": ""}
        data.update(line_data("lines", [
            {"product": self.apple.pk, "description": "", "quantity": "3", "unit": "箱", "unit_price": "1200", "tax_rate": "8"},
            {"product": self.pen.pk, "description": "ボールペン（黒）", "quantity": "10", "unit": "本", "unit_price": "150", "tax_rate": "10"},
            {"product": "", "description": "", "quantity": "1", "unit": "", "unit_price": "", "tax_rate": "10"},
        ]))
        return self.client.post(reverse("sales:create"), data)

    def test_create_sales_slip(self):
        resp = self.create_sales_slip()
        slip = SalesSlip.objects.get()
        self.assertRedirects(resp, slip.get_absolute_url())
        self.assertEqual(slip.number, "S000001")
        self.assertEqual(slip.lines.count(), 2)
        self.assertEqual(slip.lines.first().description, "りんご")  # 品名が空なら商品名を使う
        # 8%: 3600 → 税 288 / 10%: 1500 → 税 150
        self.assertEqual((slip.subtotal, slip.tax, slip.total), (Decimal(5100), Decimal(438), Decimal(5538)))

        detail = self.client.get(slip.get_absolute_url())
        self.assertContains(detail, "納品書")
        self.assertContains(detail, "5,538")

    def test_update_sales_slip_delete_line(self):
        self.create_sales_slip()
        slip = SalesSlip.objects.get()
        lines = list(slip.lines.all())
        data = {"date": "2026-10-02", "customer": self.customer.pk, "notes": "修正"}
        data.update(line_data("lines", [
            {"id": lines[0].pk, "product": self.apple.pk, "description": "りんご", "quantity": "3", "unit": "箱", "unit_price": "1200", "tax_rate": "8"},
            {"id": lines[1].pk, "product": self.pen.pk, "description": "ボールペン", "quantity": "10", "unit": "本", "unit_price": "150", "tax_rate": "10", "DELETE": "on"},
        ], initial=2))
        resp = self.client.post(reverse("sales:update", args=[slip.pk]), data)
        self.assertRedirects(resp, slip.get_absolute_url())
        slip.refresh_from_db()
        self.assertEqual(slip.lines.count(), 1)
        self.assertEqual((slip.subtotal, slip.tax, slip.total), (Decimal(3600), Decimal(288), Decimal(3888)))

    def test_slip_requires_a_line(self):
        data = {"date": "2026-10-01", "customer": self.customer.pk}
        data.update(line_data("lines", [{"product": "", "description": "", "quantity": "1", "unit_price": "", "tax_rate": "10"}]))
        resp = self.client.post(reverse("sales:create"), data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "明細を1行以上入力してください。")
        self.assertFalse(SalesSlip.objects.exists())

    def test_create_purchase_slip_numbering(self):
        for _ in range(2):
            data = {"date": "2026-10-05", "supplier": self.supplier.pk, "supplier_ref": "A-1"}
            data.update(line_data("lines", [
                {"product": self.pen.pk, "description": "ボールペン", "quantity": "100", "unit": "本", "unit_price": "100", "tax_rate": "10"},
            ]))
            self.client.post(reverse("purchases:create"), data)
        self.assertEqual(list(PurchaseSlip.objects.order_by("number").values_list("number", "total")),
                         [("P000001", Decimal(11000)), ("P000002", Decimal(11000))])

    def test_slip_list_filter_and_totals(self):
        self.create_sales_slip()
        resp = self.client.get(reverse("sales:list"), {"partner": "サンプル", "date_from": "2026-10-01"})
        self.assertContains(resp, "S000001")
        self.assertEqual(resp.context["totals"]["total"], Decimal(5538))
        resp = self.client.get(reverse("sales:list"), {"date_from": "2026-11-01"})
        self.assertNotContains(resp, "S000001")

    def test_cannot_delete_master_in_use(self):
        self.create_sales_slip()
        resp = self.client.post(reverse("customers:delete", args=[self.customer.pk]))
        self.assertRedirects(resp, reverse("customers:update", args=[self.customer.pk]))
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_dashboard_monthly_totals(self):
        today = timezone.localdate()
        self.create_sales_slip(date=today.isoformat())
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.context["this_month"]["month"], today.replace(day=1))
        self.assertEqual(resp.context["this_month"]["sales"], Decimal(5100))
