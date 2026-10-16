from core.master_views import MasterCreateView, MasterDeleteView, MasterListView, MasterUpdateView

from .forms import CustomerForm, ProductForm, SupplierForm
from .models import Customer, Product, Supplier

PARTNER_COLUMNS = (("code", "コード"), ("name", "名称"), ("phone", "電話番号"), ("address", "住所"))
PARTNER_SEARCH = ("code", "name", "kana")


class CustomerList(MasterListView):
    model, url_ns, columns, search_fields = Customer, "customers", PARTNER_COLUMNS, PARTNER_SEARCH


class CustomerCreate(MasterCreateView):
    model, url_ns, form_class = Customer, "customers", CustomerForm


class CustomerUpdate(MasterUpdateView):
    model, url_ns, form_class = Customer, "customers", CustomerForm


class CustomerDelete(MasterDeleteView):
    model, url_ns = Customer, "customers"


class SupplierList(MasterListView):
    model, url_ns, columns, search_fields = Supplier, "suppliers", PARTNER_COLUMNS, PARTNER_SEARCH


class SupplierCreate(MasterCreateView):
    model, url_ns, form_class = Supplier, "suppliers", SupplierForm


class SupplierUpdate(MasterUpdateView):
    model, url_ns, form_class = Supplier, "suppliers", SupplierForm


class SupplierDelete(MasterDeleteView):
    model, url_ns = Supplier, "suppliers"


class ProductList(MasterListView):
    model, url_ns = Product, "products"
    columns = (
        ("code", "コード"),
        ("name", "商品名"),
        ("unit", "単位"),
        ("sale_price", "標準売価"),
        ("purchase_price", "標準仕入単価"),
        ("tax_rate", "税率"),
    )


class ProductCreate(MasterCreateView):
    model, url_ns, form_class = Product, "products", ProductForm


class ProductUpdate(MasterUpdateView):
    model, url_ns, form_class = Product, "products", ProductForm


class ProductDelete(MasterDeleteView):
    model, url_ns = Product, "products"
