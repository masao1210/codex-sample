from core.forms import SlipForm, slip_line_formset
from core.slip_views import SlipCreateView, SlipDeleteView, SlipDetailView, SlipListView, SlipUpdateView

from .models import SalesLine, SalesSlip


class SalesSlipForm(SlipForm):
    partner_field = "customer"

    class Meta:
        model = SalesSlip
        fields = ["date", "customer", "notes"]


SalesLineFormSet = slip_line_formset(SalesSlip, SalesLine)


class Config:
    model = SalesSlip
    url_ns = "sales"
    partner_field = "customer"
    lead = "得意先への売上（納品）を記録します。保存すると納品書を印刷できます。"


class FormConfig(Config):
    form_class = SalesSlipForm
    formset_class = SalesLineFormSet
    price_field = "sale_price"


class SalesList(Config, SlipListView):
    pass


class SalesCreate(FormConfig, SlipCreateView):
    pass


class SalesUpdate(FormConfig, SlipUpdateView):
    pass


class SalesDetail(Config, SlipDetailView):
    template_name = "sales/detail.html"


class SalesDelete(Config, SlipDeleteView):
    pass
