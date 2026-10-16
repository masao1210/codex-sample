"""消費税の計算。

インボイス制度（適格請求書）のルールに合わせ、消費税は明細ごとではなく
「1枚の伝票につき、税率ごとに1回」端数処理する。
"""

from collections import defaultdict
from decimal import ROUND_DOWN, Decimal

from django.db import models


class TaxRate(models.IntegerChoices):
    STANDARD = 10, "10%"
    REDUCED = 8, "8%（軽減）"
    EXEMPT = 0, "非課税"


YEN = Decimal("1")


def round_yen(value):
    """1円未満を切り捨てる。"""
    return Decimal(value).quantize(YEN, rounding=ROUND_DOWN)


def line_amount(quantity, unit_price):
    """明細の金額（税抜）。"""
    return round_yen(Decimal(quantity) * Decimal(unit_price))


def summarize(lines):
    """(税率, 税抜金額) の並びから、税率ごとの内訳と合計を返す。

    戻り値:
        {
            "by_rate": [{"rate": 10, "subtotal": Decimal, "tax": Decimal}, ...],
            "subtotal": Decimal,
            "tax": Decimal,
            "total": Decimal,
        }
    """
    subtotals = defaultdict(Decimal)
    for rate, amount in lines:
        subtotals[int(rate)] += Decimal(amount)

    by_rate = []
    for rate in sorted(subtotals, reverse=True):
        subtotal = subtotals[rate]
        tax = round_yen(subtotal * rate / 100)
        by_rate.append({"rate": rate, "subtotal": subtotal, "tax": tax})

    subtotal = sum((r["subtotal"] for r in by_rate), Decimal(0))
    tax = sum((r["tax"] for r in by_rate), Decimal(0))
    return {"by_rate": by_rate, "subtotal": subtotal, "tax": tax, "total": subtotal + tax}
