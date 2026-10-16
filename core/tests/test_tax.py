from decimal import Decimal

from django.test import SimpleTestCase

from core import tax


class TaxTests(SimpleTestCase):
    def test_line_amount_rounds_down(self):
        self.assertEqual(tax.line_amount(Decimal("3"), Decimal("33.33")), Decimal("99"))

    def test_tax_is_rounded_once_per_rate(self):
        # 明細ごとに丸めると 9+9+9=27 円だが、税率ごとに合計してから丸めるので 29 円になる
        s = tax.summarize([(10, 99), (10, 99), (10, 99)])
        self.assertEqual(s["subtotal"], Decimal("297"))
        self.assertEqual(s["tax"], Decimal("29"))
        self.assertEqual(s["total"], Decimal("326"))

    def test_mixed_rates(self):
        s = tax.summarize([(10, 1000), (8, 1000), (8, 555), (0, 300)])
        self.assertEqual(
            [(r["rate"], r["subtotal"], r["tax"]) for r in s["by_rate"]],
            [(10, Decimal("1000"), Decimal("100")), (8, Decimal("1555"), Decimal("124")), (0, Decimal("300"), Decimal("0"))],
        )
        self.assertEqual(s["tax"], Decimal("224"))
        self.assertEqual(s["total"], Decimal("3079"))

    def test_empty(self):
        s = tax.summarize([])
        self.assertEqual((s["subtotal"], s["tax"], s["total"]), (0, 0, 0))
