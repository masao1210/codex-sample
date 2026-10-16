from django import forms

from .models import Customer, Product, Supplier

PARTNER_FIELDS = ["code", "name", "kana", "honorific", "postal_code", "address", "phone", "email", "notes", "is_active"]
TEXTAREA = {"notes": forms.Textarea(attrs={"rows": 3})}


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = PARTNER_FIELDS[:-2] + ["closing_day", "collection_month", "collection_day", "notes", "is_active"]
        widgets = TEXTAREA


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = PARTNER_FIELDS[:-2] + ["invoice_number", "notes", "is_active"]
        widgets = TEXTAREA


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["code", "name", "unit", "sale_price", "purchase_price", "tax_rate", "notes", "is_active"]
        widgets = TEXTAREA
