"""マスタ（得意先・仕入先・商品など）の一覧・登録・編集・削除で共通に使うビュー。

子クラスでは model / url_ns / columns（一覧に出す (フィールド名, 見出し) の並び）を指定する。
"""

from django.contrib import messages
from django.db.models import ProtectedError, Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views import generic


class MasterMixin:
    url_ns = ""
    search_fields = ("code", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.model._meta.verbose_name
        ctx["lead"] = getattr(self, "lead", "")
        ctx["url_ns"] = self.url_ns
        return ctx

    def get_success_url(self):
        return reverse(f"{self.url_ns}:list")


class MasterListView(MasterMixin, generic.ListView):
    template_name = "core/master_list.html"
    paginate_by = 50
    columns = ()

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            cond = Q()
            for f in self.search_fields:
                cond |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(cond)
        if not self.request.GET.get("inactive"):
            qs = qs.filter(is_active=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["columns"] = self.columns
        ctx["rows"] = [(obj, [display_value(obj, f) for f, _ in self.columns]) for obj in ctx["object_list"]]
        return ctx


def display_value(obj, field):
    """choices を持つフィールドは表示用の文字列にする。"""
    get_display = getattr(obj, f"get_{field}_display", None)
    return get_display() if get_display else getattr(obj, field)


class MasterCreateView(MasterMixin, generic.CreateView):
    template_name = "core/master_form.html"

    def form_valid(self, form):
        messages.success(self.request, f"{self.model._meta.verbose_name}を登録しました。")
        return super().form_valid(form)


class MasterUpdateView(MasterMixin, generic.UpdateView):
    template_name = "core/master_form.html"

    def form_valid(self, form):
        messages.success(self.request, f"{self.model._meta.verbose_name}を更新しました。")
        return super().form_valid(form)


class MasterDeleteView(MasterMixin, generic.DeleteView):
    template_name = "core/confirm_delete.html"

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "伝票で使われているため削除できません。使わなくなった場合は「有効」のチェックを外してください。",
            )
            return redirect(reverse(f"{self.url_ns}:update", args=[self.object.pk]))
        messages.success(self.request, f"{self.model._meta.verbose_name}を削除しました。")
        return response
