from django import forms
from django.utils import timezone

from masters.models import DAY_CHOICES, END_OF_MONTH, Customer

from .models import Payment


class ClosingForm(forms.Form):
    month = forms.CharField(label="締める年月", widget=forms.DateInput(attrs={"type": "month"}))
    closing_day = forms.TypedChoiceField(label="締日", choices=DAY_CHOICES, coerce=int, initial=END_OF_MONTH)
    issue_date = forms.DateField(
        label="請求日", required=False, widget=forms.DateInput(attrs={"type": "date"}),
        help_text="空欄なら締日を請求日にします。",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            today = timezone.localdate()
            self.initial["month"] = f"{today:%Y-%m}"

    def clean_month(self):
        value = self.cleaned_data["month"]
        try:
            y, m = map(int, value.split("-"))
            if not (1 <= m <= 12 and 2000 <= y <= 2100):
                raise ValueError
        except ValueError:
            raise forms.ValidationError("年月を YYYY-MM の形で入力してください。")
        return value

    @property
    def year_month(self):
        y, m = map(int, self.cleaned_data["month"].split("-"))
        return y, m


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["date", "customer", "method", "amount", "fee", "notes"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Customer.objects.filter(is_active=True)
        if self.instance.customer_id:
            qs = qs | Customer.objects.filter(pk=self.instance.customer_id)
        self.fields["customer"].queryset = qs.distinct()

    def clean(self):
        data = super().clean()
        amount, fee = data.get("amount"), data.get("fee") or 0
        if amount is not None and amount + fee <= 0:
            raise forms.ValidationError("入金額（と手数料・値引）の合計は1円以上にしてください。")
        return data
