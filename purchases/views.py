from core.forms import SlipForm, slip_line_formset
from core.slip_views import SlipCreateView, SlipDeleteView, SlipDetailView, SlipListView, SlipUpdateView

from .models import PurchaseLine, PurchaseSlip


class PurchaseSlipForm(SlipForm):
    partner_field = "supplier"

    class Meta:
        model = PurchaseSlip
        fields = ["date", "supplier", "supplier_ref", "notes"]


PurchaseLineFormSet = slip_line_formset(PurchaseSlip, PurchaseLine)


class Config:
    model = PurchaseSlip
    url_ns = "purchases"
    partner_field = "supplier"


class FormConfig(Config):
    form_class = PurchaseSlipForm
    formset_class = PurchaseLineFormSet
    price_field = "purchase_price"


class PurchaseList(Config, SlipListView):
    pass


class PurchaseCreate(FormConfig, SlipCreateView):
    pass


class PurchaseUpdate(FormConfig, SlipUpdateView):
    pass


class PurchaseDetail(Config, SlipDetailView):
    template_name = "purchases/detail.html"


class PurchaseDelete(Config, SlipDeleteView):
    pass
