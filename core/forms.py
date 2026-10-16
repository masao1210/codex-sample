from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory


class SlipForm(forms.ModelForm):
    """伝票ヘッダのフォーム。取引先は有効なもの（と編集中の伝票で使っているもの）だけを選べる。"""

    partner_field = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields[self.partner_field]
        current = getattr(self.instance, f"{self.partner_field}_id", None)
        qs = field.queryset.filter(is_active=True)
        if current:
            qs = qs | field.queryset.filter(pk=current)
        field.queryset = qs.distinct()
        self.fields["date"].widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        self.fields["notes"].widget = forms.Textarea(attrs={"rows": 2})


class SlipLineForm(forms.ModelForm):
    LINE_FIELDS = ["product", "description", "quantity", "unit", "unit_price", "tax_rate"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        product = self.fields["product"]
        current = self.instance.product_id
        qs = product.queryset.filter(is_active=True)
        if current:
            qs = qs | product.queryset.filter(pk=current)
        product.queryset = qs.distinct()
        self.fields["description"].required = False
        self.fields["unit_price"].required = False

    def clean(self):
        data = super().clean()
        product = data.get("product")
        if product and not data.get("description"):
            data["description"] = product.name
        if not data.get("description") and not data.get("DELETE"):
            self.add_error("description", "品名を入力するか、商品を選んでください。")
        if data.get("unit_price") is None and not data.get("DELETE"):
            self.add_error("unit_price", "単価を入力してください。")
        return data


class BaseSlipLineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        live = [
            f for f in self.forms if (f.instance.pk or f.has_changed()) and not self._should_delete_form(f)
        ]
        if not live:
            raise forms.ValidationError("明細を1行以上入力してください。")

    def save(self, commit=True):
        for i, form in enumerate(self.forms, start=1):
            form.instance.line_no = i
        return super().save(commit)


def slip_line_formset(parent_model, line_model):
    return inlineformset_factory(
        parent_model,
        line_model,
        form=SlipLineForm,
        formset=BaseSlipLineFormSet,
        fields=SlipLineForm.LINE_FIELDS,
        extra=5,
        can_delete=True,
    )
