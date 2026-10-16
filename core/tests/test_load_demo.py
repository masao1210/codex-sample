from io import StringIO

from django.core.management import call_command
from django.db.models import F
from django.test import TestCase

from masters.models import Customer, Product
from purchases.models import PurchaseSlip
from sales.models import SalesSlip


class LoadDemoTests(TestCase):
    def test_creates_100_customers_and_products(self):
        call_command("load_demo", stdout=StringIO())
        self.assertEqual(Customer.objects.count(), 100)
        self.assertEqual(Product.objects.count(), 100)
        self.assertEqual(Customer.objects.values("name").distinct().count(), 100)
        self.assertEqual(SalesSlip.objects.count(), 24)
        self.assertEqual(PurchaseSlip.objects.count(), 12)
        self.assertFalse(Product.objects.filter(purchase_price__gte=F("sale_price")).exists())

    def test_running_twice_does_not_duplicate(self):
        call_command("load_demo", stdout=StringIO())
        Customer.objects.filter(code="C001").update(name="手で直した名前")
        call_command("load_demo", stdout=StringIO())
        self.assertEqual(Customer.objects.count(), 100)
        self.assertEqual(SalesSlip.objects.count(), 24)
        self.assertEqual(Customer.objects.get(code="C001").name, "手で直した名前")
