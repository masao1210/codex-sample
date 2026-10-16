"""画面部品用のテンプレートタグ。{% icon "home" %} のように使う（settings で builtins に登録済み）。"""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# 線で描くシンプルなアイコン（24×24）。色は文字色に合わせる。
ICONS = {
    "home": '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
    "sales": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "purchases": '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5"/><path d="M12 13v8"/>',
    "payments": '<rect x="2" y="6" width="20" height="13" rx="2"/><path d="M2 10h20"/><path d="M16 15h2"/>',
    "invoice": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M8 13h8M8 17h6"/>',
    "closing": '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/><path d="m9 15 2 2 4-4"/>',
    "receivables": '<path d="M4 20V11M10 20V5M16 20v-6M22 20H2"/>',
    "customers": '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M16 4.5a4 4 0 0 1 0 7M22 21a7 7 0 0 0-4-6.3"/>',
    "suppliers": '<path d="M3 21V10l6 3v-3l6 3V4h6v17z"/><path d="M3 21h18"/>',
    "products": '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="8" cy="8" r="1.5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "print": '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13 7 4 4"/>',
    "trash": '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    "back": '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
    "admin": '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/>',
    "menu": '<path d="M3 6h18M3 12h18M3 18h18"/>',
    "check": '<path d="m5 12 5 5 9-10"/>',
    "alert": '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 17h.01"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "cancel": '<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6M9 9l6 6"/>',
}


@register.simple_tag
def icon(name, extra_class=""):
    return format_html(
        '<svg class="icon {}" viewBox="0 0 24 24" aria-hidden="true">{}</svg>',
        extra_class, mark_safe(ICONS[name]),
    )


@register.filter
def yen(value):
    """金額を「¥1,234」の形にする。マイナスは「-¥1,234」。"""
    try:
        n = int(round(float(value or 0)))
    except (TypeError, ValueError):
        return value
    return f"-¥{-n:,}" if n < 0 else f"¥{n:,}"
