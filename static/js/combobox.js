/* Search box for a <select>: type part of a name and pick from the matches.
   The <select> stays in the page, hidden, so saving the form works as before. Works offline. */
(function () {
  "use strict";
  let counter = 0;

  function enhance(select) {
    if (!select || select.dataset.combo) return;
    select.dataset.combo = "1";
    const id = select.id || "combo" + (++counter);
    const options = () => [...select.options].filter((o) => o.value !== "");
    const placeholder = [...select.options].find((o) => o.value === "");

    const box = document.createElement("div");
    box.className = "combo";
    const input = document.createElement("input");
    input.type = "text";
    input.className = "form-control combo-input";
    input.id = id + "_search";
    input.autocomplete = "off";
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.placeholder = placeholder ? placeholder.text : "Type to search";
    const list = document.createElement("ul");
    list.className = "combo-list";
    list.id = id + "_list";
    list.setAttribute("role", "listbox");
    list.hidden = true;
    input.setAttribute("aria-controls", list.id);

    select.hidden = true;
    select.tabIndex = -1;
    select.parentNode.insertBefore(box, select);
    box.append(input, list, select);
    const label = document.querySelector(`label[for="${select.id}"]`);
    if (label) label.htmlFor = input.id;

    let matches = [], active = -1;
    const chosenText = () => (select.selectedOptions[0] && select.value !== "" ? select.selectedOptions[0].text : "");
    input.value = chosenText();

    function show(query) {
      const q = query.trim().toLowerCase();
      matches = options().filter((o) => !q || o.text.toLowerCase().includes(q));
      active = matches.length ? 0 : -1;
      list.innerHTML = matches.length
        ? matches.map((o, i) => `<li role="option" id="${id}_o${i}" data-i="${i}" class="${i === active ? "active" : ""}">${escape(o.text)}</li>`).join("")
        : `<li class="combo-none">No match</li>`;
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
      mark();
    }
    function mark() {
      [...list.querySelectorAll("li[data-i]")].forEach((li) => li.classList.toggle("active", +li.dataset.i === active));
      const li = list.querySelector(`li[data-i="${active}"]`);
      if (li) { input.setAttribute("aria-activedescendant", li.id); li.scrollIntoView({ block: "nearest" }); }
      else input.removeAttribute("aria-activedescendant");
    }
    function close() {
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }
    function choose(option) {
      close();
      input.value = option.text;
      if (select.value === option.value) return;
      select.value = option.value;
      select.dispatchEvent(new Event("input", { bubbles: true }));
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }

    input.addEventListener("focus", () => { input.select(); show(""); });
    input.addEventListener("input", () => show(input.value));
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (list.hidden) { show(input.value); return; }
        if (!matches.length) return;
        active = (active + (e.key === "ArrowDown" ? 1 : -1) + matches.length) % matches.length;
        mark();
      } else if (e.key === "Enter") {
        if (!list.hidden) e.preventDefault();
        if (!list.hidden && matches[active]) choose(matches[active]);
      } else if (e.key === "Escape") {
        close();
        input.value = chosenText();
      }
    });
    input.addEventListener("blur", () => setTimeout(() => {
      // Only a name from the list can be chosen. Anything else goes back to the chosen name.
      close();
      input.value = chosenText();
    }, 150));
    list.addEventListener("mousedown", (e) => {
      const li = e.target.closest("li[data-i]");
      e.preventDefault();
      if (li) choose(matches[+li.dataset.i]);
    });
  }

  function escape(v) {
    return String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  window.Combo = { enhance };
})();
