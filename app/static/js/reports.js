// =============================================================================
// reports.js — منتقي نطاق التصدير المخصّص (الكل / كتيبة / سرية / فصيل)
// يحدّث رابطي Excel و PDF معاً
// =============================================================================
(function () {
  "use strict";

  var typeSelect = document.getElementById("exportScopeType");
  var battalionField = document.getElementById("exportBattalionField");
  var companyField = document.getElementById("exportCompanyField");
  var platoonField = document.getElementById("exportPlatoonField");
  var battalionSelect = document.getElementById("exportBattalionSelect");
  var companySelect = document.getElementById("exportCompanySelect");
  var platoonSelect = document.getElementById("exportPlatoonSelect");
  var exportBtn = document.getElementById("exportScopeBtn");
  var printBtn = document.getElementById("printScopeBtn");

  if (!typeSelect || !exportBtn) return;

  var EXPORT_URL = {
    full: function () { return "/export/full"; },
    battalion: function (id) { return "/export/battalion/" + id; },
    company: function (id) { return "/export/company/" + id; },
    platoon: function (id) { return "/export/platoon/" + id; },
  };
  var PRINT_URL = {
    full: function () { return "/print/full"; },
    battalion: function (id) { return "/print/battalion/" + id; },
    company: function (id) { return "/print/company/" + id; },
    platoon: function (id) { return "/print/platoon/" + id; },
  };

  function fillSelect(select, items, placeholder) {
    select.innerHTML = "";
    if (!items.length) {
      var opt = document.createElement("option");
      opt.value = "";
      opt.textContent = placeholder;
      select.appendChild(opt);
      return;
    }
    items.forEach(function (item) {
      var opt = document.createElement("option");
      opt.value = item.id;
      opt.textContent = item.name;
      select.appendChild(opt);
    });
  }

  function setLink(btn, urlFn, type, val) {
    if (!btn) return;
    if (type === "full") btn.setAttribute("href", urlFn.full());
    else btn.setAttribute("href", val ? urlFn[type](val) : "#");
  }

  function refreshLinks() {
    var type = typeSelect.value;
    var val = type === "battalion" ? battalionSelect.value
            : type === "company" ? companySelect.value
            : type === "platoon" ? platoonSelect.value : "";
    setLink(exportBtn, EXPORT_URL, type, val);
    setLink(printBtn, PRINT_URL, type, val);
  }

  function loadCompaniesFor(battalionId, cb) {
    fetch("/api/companies/" + battalionId).then(function (r) { return r.json(); }).then(function (items) {
      fillSelect(companySelect, items, "لا توجد سرايا");
      if (cb) cb();
    });
  }
  function loadPlatoonsFor(companyId, cb) {
    fetch("/api/platoons/" + companyId).then(function (r) { return r.json(); }).then(function (items) {
      fillSelect(platoonSelect, items, "لا توجد فصائل");
      if (cb) cb();
    });
  }

  function applyTypeVisibility() {
    var type = typeSelect.value;
    battalionField.style.display = type === "full" ? "none" : "";
    companyField.style.display = (type === "company" || type === "platoon") ? "" : "none";
    platoonField.style.display = type === "platoon" ? "" : "none";
    if (type === "company" || type === "platoon") {
      loadCompaniesFor(battalionSelect.value, function () {
        if (type === "platoon") loadPlatoonsFor(companySelect.value, refreshLinks);
        else refreshLinks();
      });
    } else {
      refreshLinks();
    }
  }

  typeSelect.addEventListener("change", applyTypeVisibility);
  battalionSelect.addEventListener("change", function () {
    loadCompaniesFor(battalionSelect.value, function () {
      if (typeSelect.value === "platoon") loadPlatoonsFor(companySelect.value, refreshLinks);
      else refreshLinks();
    });
  });
  companySelect.addEventListener("change", function () {
    if (typeSelect.value === "platoon") loadPlatoonsFor(companySelect.value, refreshLinks);
    else refreshLinks();
  });
  platoonSelect.addEventListener("change", refreshLinks);

  applyTypeVisibility();
})();
