(function () {
  "use strict";
  /* FBR can't read the inch sign, so it becomes in as it's typed, for example 98in. */
  const name = document.getElementById("id_name");
  if (name) name.addEventListener("input", () => {
    if (!name.value.includes('"')) return;
    const at = name.selectionStart + (name.value.slice(0, name.selectionStart).split('"').length - 1);
    name.value = name.value.replace(/"/g, "in");
    name.setSelectionRange(at, at);
  });
  /* Shows the rate text FBR will get, the same way the server makes it. */
  const out = document.getElementById("ratePreview");
  const rate = document.getElementById("id_rate_percent");
  const sale = document.getElementById("id_sale_type");
  if (!out || !rate || !sale || out.dataset.kept) return;
  const update = () => {
    if (String(sale.value).trim().toLowerCase().startsWith("exempt")) { out.textContent = "Exempt"; return; }
    const n = parseFloat(rate.value);
    out.textContent = (isFinite(n) ? String(Math.round(n * 100) / 100) : "0") + "%";
  };
  rate.addEventListener("input", update);
  sale.addEventListener("change", update);
  update();
})();
