(function () {
  "use strict";
  const form = document.getElementById("invForm");
  if (!form) return;

  const read = (id) => JSON.parse(document.getElementById(id).textContent);
  const PRODUCTS = read("products-data");
  const KINDS = read("customers-data");
  const QUALITIES = read("qualities-data");
  /* A quality used before brings back the rate it was last sold at. The rate can still be changed. */
  const pastQuality = (text) => QUALITIES.find((q) => q.quality.toLowerCase() === String(text).trim().toLowerCase());
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const rs = (paisa) => "Rs " + (paisa / 100).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const num = (v) => parseFloat(v) || 0;
  const product = (id) => PRODUCTS.find((p) => p.id === +id);
  /* The quantity goes to FBR in the product's unit, so the choices follow it. */
  const soldByFor = (p, wanted) => {
    if (p.metre) return "metre";
    if (p.kg) return "kg";
    return wanted === "lot" ? "lot" : "piece";
  };
  const defaultProduct = () => PRODUCTS.find((p) => p.metre) || PRODUCTS.find((p) => p.kg) || PRODUCTS[0];

  let nextId = 1;
  const newLine = (d) => {
    const pid = d && product(d.product) ? +d.product : defaultProduct().id;
    return {
      id: nextId++,
      product: pid,
      sold_by: soldByFor(product(pid), d && d.sold_by),
      quantity: (d && d.quantity) || "1",
      pieces_per_lot: (d && d.pieces_per_lot) || "",
      price: (d && d.price) || product(pid).price,
      discount: (d && d.discount) || "0",
      quality: (d && d.quality) || "",
    };
  };
  const lines = [];
  const unitOptions = (l) => {
    const p = product(l.product);
    if (p.kg) return `<option value="kg" selected>KG</option>`;
    if (p.metre) return `<option value="metre" selected>Metre</option>`;
    const uom = String(p.uom || "").trim();
    const piece = !uom || uom.toLowerCase() === "numbers, pieces, units" ? "Piece" : uom;
    return `<option value="piece" ${l.sold_by === "piece" ? "selected" : ""}>${esc(piece)}</option><option value="lot" ${l.sold_by === "lot" ? "selected" : ""}>Lot</option>`;
  };

  function render() {
    $("lines").innerHTML = lines.map((l) => {
      const opts = PRODUCTS.map((p) => `<option value="${p.id}" ${p.id === l.product ? "selected" : ""}>${esc(p.name)}</option>`).join("");
      const lot = l.sold_by === "lot"
        ? `<div class="lot-pieces"><label class="form-label" for="pl${l.id}">Pieces in each lot</label><input class="form-control num" id="pl${l.id}" data-l="${l.id}" data-f="pieces_per_lot" type="number" min="1" step="1" value="${esc(l.pieces_per_lot)}"></div>`
        : "";
      const discount = l.showDiscount || num(l.discount) > 0
        ? `<div class="line-discount"><label class="form-label" for="dc${l.id}">Discount</label><input class="form-control num" id="dc${l.id}" data-l="${l.id}" data-f="discount" type="number" min="0" step="0.01" value="${esc(l.discount)}"></div>`
        : `<button class="btn btn-link add-discount" type="button" data-disc="${l.id}"><i class="bi bi-plus-lg"></i> Discount</button>`;
      return `<div class="line">
        <div class="f-product"><label class="form-label" for="pr${l.id}">Product</label><select class="form-select" id="pr${l.id}" data-l="${l.id}" data-f="product">${opts}</select><div class="hs-cap">HS Code: ${esc(product(l.product).hs || "-")}</div></div>
        <div class="line-quality"><label class="form-label" for="ql${l.id}">Description</label><input class="form-control" id="ql${l.id}" data-l="${l.id}" data-f="quality" list="qualityList" maxlength="150" autocomplete="off" placeholder="For example 76x68/30x30 98&quot;" value="${esc(l.quality)}"></div>
        <div class="f-qty"><label class="form-label" for="qt${l.id}">Qty</label><input class="form-control num" id="qt${l.id}" data-l="${l.id}" data-f="quantity" type="number" min="0" step="any" value="${esc(l.quantity)}"></div>
        <div class="f-unit"><label class="form-label" for="un${l.id}">Unit</label><select class="form-select" id="un${l.id}" data-l="${l.id}" data-f="unit">${unitOptions(l)}</select></div>
        <div class="f-rate"><label class="form-label" for="dp${l.id}">Rate</label><input class="form-control num" id="dp${l.id}" data-l="${l.id}" data-f="price" type="number" min="0" step="0.01" value="${esc(l.price)}"></div>
        <button class="rm" type="button" data-rm="${l.id}" aria-label="Remove this item" ${lines.length === 1 ? "disabled" : ""}><i class="bi bi-x-lg"></i></button>
        ${lot}${discount}
        <div class="line-meta"><span id="meta${l.id}"></span><strong id="amt${l.id}"></strong></div>
      </div>`;
    }).join("");
    /* Type to search the product list on each line. */
    if (window.Combo) lines.forEach((l) => window.Combo.enhance($("pr" + l.id)));
    calc();
  }

  /* On-screen totals only. The server works out the saved figures with Decimal. */
  function calc() {
    const kind = KINDS[$("buyer").value];
    let excl = 0, st = 0, ft = 0, disc = 0, kg = 0, mtrs = 0;
    lines.forEach((l) => {
      const p = product(l.product);
      const pieces = num(l.quantity) * (l.sold_by === "lot" ? num(l.pieces_per_lot) : 1);
      const v = Math.round(pieces * num(l.price) * 100);
      const d = Math.round(num(l.discount) * 100);
      const s = Math.round((v - d) * num(p.rate) / 100);
      const f = kind === "unregistered" ? Math.round((v - d) * num(p.further) / 100) : 0;
      const fed = Math.round((v - d) * num(p.fed) / 100);
      excl += v; st += s + fed; ft += f; disc += d;
      const meta = $("meta" + l.id), amt = $("amt" + l.id);
      kg += l.sold_by === "kg" ? pieces : 0;
      mtrs += l.sold_by === "metre" ? pieces : 0;
      if (meta) meta.textContent = `Value ${rs(v)}, sales tax ${num(p.rate)}%`;
      if (amt) amt.textContent = rs(v + s + f + fed - d);
    });
    $("tKgRow").style.display = kg ? "" : "none";
    $("tKg").textContent = kg.toLocaleString("en-PK") + " KG";
    $("tMtrRow").style.display = mtrs ? "" : "none";
    $("tMtr").textContent = mtrs.toLocaleString("en-PK") + " MTRS";
    $("tExcl").textContent = rs(excl);
    $("tST").textContent = rs(st);
    $("tFT").textContent = rs(ft);
    $("tDisc").textContent = "- " + rs(disc);
    $("tGrand").textContent = rs(excl + st + ft - disc);
    $("exportNote").hidden = kind !== "foreign";
  }

  $("lines").addEventListener("input", (e) => {
    const t = e.target, l = lines.find((x) => x.id === +t.dataset.l);
    if (!l) return;
    const f = t.dataset.f;
    if (f === "product") { l.product = +t.value; l.price = product(l.product).price; const p = product(l.product); l.sold_by = soldByFor(p, l.sold_by); render(); }
    else if (f === "unit") {
      if (["piece", "lot", "metre", "kg"].includes(t.value)) l.sold_by = t.value;
      render();
    }
    else if (f === "quality") {
      /* FBR can't read the inch sign, so it becomes in as it's typed, for example 98in. */
      if (t.value.includes('"')) {
        const at = t.selectionStart + (t.value.slice(0, t.selectionStart).split('"').length - 1);
        t.value = t.value.replace(/"/g, "in");
        t.setSelectionRange(at, at);
      }
      l.quality = t.value;
      const past = pastQuality(t.value);
      if (past) { l.price = past.rate; const rate = $("dp" + l.id); if (rate) rate.value = past.rate; }
      calc();
    }
    else { l[f] = t.value; calc(); }
  });
  $("lines").addEventListener("click", (e) => {
    const d = e.target.closest("[data-disc]");
    if (d) {
      lines.find((x) => x.id === +d.dataset.disc).showDiscount = true;
      render();
      $("dc" + d.dataset.disc).focus();
      return;
    }
    const b = e.target.closest("[data-rm]");
    if (!b) return;
    lines.splice(lines.findIndex((x) => x.id === +b.dataset.rm), 1);
    render();
  });
  $("addLine").addEventListener("click", () => { lines.push(newLine()); render(); });
  $("buyer").addEventListener("change", calc);
  form.addEventListener("submit", () => {
    $("offlineField").value = navigator.onLine ? "0" : "1";
    $("linesField").value = JSON.stringify(lines.map((l) => ({
      product: l.product, sold_by: l.sold_by, quantity: l.quantity,
      pieces_per_lot: l.pieces_per_lot, price: l.price, discount: l.discount, quality: l.quality,
    })));
  });

  const initial = read("initial-lines");
  (Array.isArray(initial) && initial.length ? initial : [null]).forEach((d) => {
    lines.push(newLine(d));
  });
  /* The date in words, so day and month can't be mixed up, with a warning for old or future dates. */
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const showDate = () => {
    const box = $("dateWords"), m = /^(\d{4})-(\d{2})-(\d{2})$/.exec($("date").value || "");
    if (!box) return;
    if (!m) { box.textContent = ""; box.className = "date-words"; return; }
    const d = new Date(+m[1], +m[2] - 1, +m[3]);
    const now = new Date(); const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const age = Math.round((today - d) / 86400000);
    let text = `${m[3]}-${MONTHS[d.getMonth()]}-${m[1]} (${DAYS[d.getDay()]})`, warn = "";
    if (age > 30) warn = `This date is ${age} days old. Check it before saving.`;
    else if (age < 0) warn = "This date is in the future. Check it before saving.";
    box.innerHTML = `<b>${text}</b>${warn ? `<span class="date-warn">${warn}</span>` : ""}`;
    box.className = "date-words" + (warn ? " warn" : "");
  };
  $("date").addEventListener("input", showDate);
  $("date").addEventListener("change", showDate);
  showDate();
  if (window.Combo) window.Combo.enhance($("buyer"));
  render();
})();
