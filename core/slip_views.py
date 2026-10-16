"""伝票（売上・仕入など）の一覧・入力・表示・削除で共通に使うビュー。

子クラスでは model / url_ns / partner_field（"customer" など）を指定し、
入力ビューではさらに form_class / formset_class / price_field（商品マスタの単価フィールド）を指定する。
"""

from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views import generic

from masters.models import Product


class SlipMixin:
    url_ns = ""
    partner_field = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.model._meta.verbose_name
        ctx["url_ns"] = self.url_ns
        ctx["partner_field"] = self.partner_field
        ctx["partner_label"] = self.model._meta.get_field(self.partner_field).verbose_name
        return ctx


class SlipListView(SlipMixin, generic.ListView):
    template_name = "core/slip_list.html"
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset().select_related(self.partner_field)
        params = self.request.GET
        if date_from := parse_date(params.get("date_from", "")):
            qs = qs.filter(date__gte=date_from)
        if date_to := parse_date(params.get("date_to", "")):
            qs = qs.filter(date__lte=date_to)
        if partner := params.get("partner", "").strip():
            qs = qs.filter(**{f"{self.partner_field}__name__icontains": partner})
        if number := params.get("number", "").strip():
            qs = qs.filter(number__icontains=number)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["totals"] = self.object_list.aggregate(subtotal=Sum("subtotal"), tax=Sum("tax"), total=Sum("total"))
        ctx["slips"] = [(slip, getattr(slip, self.partner_field)) for slip in ctx["object_list"]]
        return ctx


class SlipFormMixin(SlipMixin):
    template_name = "core/slip_form.html"
    formset_class = None
    price_field = ""

    def get_formset(self):
        return self.formset_class(self.request.POST or None, instance=self.object, prefix="lines")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("formset", self.get_formset())
        ctx["products"] = {
            p.pk: {"name": p.name, "unit": p.unit, "price": str(getattr(p, self.price_field)), "tax_rate": p.tax_rate}
            for p in Product.objects.filter(is_active=True)
        }
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if "pk" in kwargs else None
        form = self.get_form()
        formset = self.get_formset()
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
                self.object.recalculate()
            messages.success(request, f"{self.model._meta.verbose_name} {self.object.number} を保存しました。")
            return redirect(self.object.get_absolute_url())
        return self.render_to_response(self.get_context_data(form=form, formset=formset))


class SlipCreateView(SlipFormMixin, generic.CreateView):
    pass


class SlipUpdateView(SlipFormMixin, generic.UpdateView):
    pass


class SlipDetailView(SlipMixin, generic.DetailView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["partner"] = getattr(self.object, self.partner_field)
        ctx["lines"] = self.object.lines.all()
        ctx["summary"] = self.object.tax_summary()
        return ctx


class SlipDeleteView(SlipMixin, generic.DeleteView):
    template_name = "core/confirm_delete.html"

    def get_success_url(self):
        return reverse(f"{self.url_ns}:list")

    def form_valid(self, form):
        messages.success(self.request, f"{self.model._meta.verbose_name} {self.object.number} を削除しました。")
        return super().form_valid(form)
