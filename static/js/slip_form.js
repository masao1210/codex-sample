// 伝票入力画面: 商品を選ぶと品名・単位・単価・税率を自動入力し、金額と消費税をその場で計算する。
// 計算ルールはサーバー側（core/tax.py）と同じ: 明細金額は1円未満切り捨て、消費税は税率ごとに合計してから切り捨て。
(function () {
  const products = JSON.parse(document.getElementById("product-data").textContent);
  const rows = document.getElementById("line-rows");
  const template = document.getElementById("line-template");
  const totalForms = document.querySelector('input[name="lines-TOTAL_FORMS"]');
  const yen = (n) => n.toLocaleString("ja-JP");

  const field = (row, name) => row.querySelector(`[name$="-${name}"]`);

  function recalc() {
    const byRate = {};
    rows.querySelectorAll("tr.line").forEach((row) => {
      const qty = parseFloat(field(row, "quantity").value) || 0;
      const price = parseFloat(field(row, "unit_price").value) || 0;
      const deleted = field(row, "DELETE")?.checked;
      const filled = field(row, "description").value || field(row, "product").value;
      const amount = Math.floor(qty * price);
      row.querySelector(".line-amount").textContent = filled ? yen(amount) : "";
      row.classList.toggle("deleted", !!deleted);
      if (!filled || deleted) return;
      const rate = parseInt(field(row, "tax_rate").value, 10);
      byRate[rate] = (byRate[rate] || 0) + amount;
    });

    let subtotal = 0, taxTotal = 0;
    const parts = [];
    Object.keys(byRate).map(Number).sort((a, b) => b - a).forEach((rate) => {
      const tax = Math.floor((byRate[rate] * rate) / 100);
      subtotal += byRate[rate];
      taxTotal += tax;
      parts.push(`${rate}%対象 ${yen(byRate[rate])}（税 ${yen(tax)}）`);
    });
    document.getElementById("t-subtotal").textContent = yen(subtotal);
    document.getElementById("t-by-rate").textContent = parts.join(" / ");
    document.getElementById("t-tax").textContent = yen(taxTotal);
    document.getElementById("t-total").textContent = yen(subtotal + taxTotal);
  }

  function onProductChange(row) {
    const p = products[field(row, "product").value];
    if (!p) return;
    field(row, "description").value = p.name;
    field(row, "unit").value = p.unit;
    field(row, "unit_price").value = p.price;
    field(row, "tax_rate").value = p.tax_rate;
  }

  rows.addEventListener("change", (e) => {
    if (e.target.name?.endsWith("-product")) onProductChange(e.target.closest("tr"));
    recalc();
  });
  rows.addEventListener("input", recalc);

  document.getElementById("add-line").addEventListener("click", () => {
    const index = parseInt(totalForms.value, 10);
    const html = template.innerHTML.replace(/__prefix__/g, index);
    rows.insertAdjacentHTML("beforeend", html);
    totalForms.value = index + 1;
    recalc();
  });

  recalc();
})();
