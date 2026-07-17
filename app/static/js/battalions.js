// =============================================================================
// battalions.js — شجرة الهيكل التنظيمي
//   - نقرة واحدة: تحديد + طي/فتح
//   - نقرة مزدوجة: فتح صفحة الطلاب
//   - لوحة الأزرار: إضافة/حذف/تصدير Excel + PDF
// =============================================================================

(function () {
  "use strict";

  var tree = document.getElementById("orgTree");
  if (!tree) return;

  /* ---- 1) طي/فتح الفروع ---- */
  tree.addEventListener("click", function (e) {
    var toggleBtn = e.target.closest("[data-tree-toggle]");
    if (toggleBtn) {
      e.stopPropagation();
      var targetId = toggleBtn.getAttribute("data-tree-toggle");
      var target = document.getElementById(targetId);
      if (target) {
        target.classList.toggle("is-collapsed");
        var icon = toggleBtn.querySelector("use");
        var collapsed = target.classList.contains("is-collapsed");
        if (icon) {
          icon.setAttribute("href", collapsed ? "#icon-chevron-left" : "#icon-chevron-down");
          icon.setAttribute("xlink:href", collapsed ? "#icon-chevron-left" : "#icon-chevron-down");
        }
      }
    }
  });

  /* ---- 2) عناصر لوحة الأزرار ---- */
  var statusEl = document.getElementById("selectionStatus");
  var btnAddCompany = document.getElementById("btnAddCompany");
  var btnAddPlatoon = document.getElementById("btnAddPlatoon");
  var btnDeleteSelected = document.getElementById("btnDeleteSelected");
  var btnExportSelected = document.getElementById("btnExportSelected");
  var btnPrintSelected = document.getElementById("btnPrintSelected");
  var deleteForm = document.getElementById("deleteSelectedForm");
  var addCompanyBattalionId = document.getElementById("addCompanyBattalionId");
  var addPlatoonCompanyId = document.getElementById("addPlatoonCompanyId");

  var TYPE_LABEL = { battalion: "كتيبة", company: "سرية", platoon: "فصيل" };
  var VIEW_URL = {
    battalion: function (id) { return "/battalions/" + id + "/students"; },
    company: function (id) { return "/companies/" + id + "/students"; },
    platoon: function (id) { return "/platoons/" + id; },
  };
  var EXPORT_URL = {
    battalion: function (id) { return "/export/battalion/" + id; },
    company: function (id) { return "/export/company/" + id; },
    platoon: function (id) { return "/export/platoon/" + id; },
  };
  var PRINT_URL = {
    battalion: function (id) { return "/print/battalion/" + id; },
    company: function (id) { return "/print/company/" + id; },
    platoon: function (id) { return "/print/platoon/" + id; },
  };
  var DELETE_URL = {
    battalion: function (id) { return "/battalions/" + id + "/delete"; },
    company: function (id) { return "/companies/" + id + "/delete"; },
    platoon: function (id) { return "/platoons/" + id + "/delete"; },
  };

  var selected = null;

  function setEnabled(el, enabled) {
    if (!el) return;
    if (el.tagName === "A") {
      el.style.pointerEvents = enabled ? "" : "none";
      el.style.opacity = enabled ? "" : ".6";
    } else {
      el.disabled = !enabled;
    }
  }

  function clearSelectionVisual() {
    tree.querySelectorAll(".tree-row.is-selected").forEach(function (r) { r.classList.remove("is-selected"); });
  }

  function selectNode(row) {
    var type = row.getAttribute("data-node-type");
    var id = row.getAttribute("data-node-id");
    var label = row.getAttribute("data-node-label");
    var battalionId = row.getAttribute("data-battalion-id");
    var companyId = row.getAttribute("data-company-id");

    if (selected && selected.type === type && selected.id === id) {
      selected = null;
      clearSelectionVisual();
      updatePanel(null);
      return;
    }

    clearSelectionVisual();
    row.classList.add("is-selected");
    selected = { type: type, id: id, label: label, battalionId: battalionId, companyId: companyId };
    updatePanel(selected);
  }

  function updatePanel(sel) {
    if (!sel) {
      statusEl.textContent = "لم يتم تحديد عنصر — انقر مرتين لفتح صفحة الطلاب";
      setEnabled(btnAddCompany, false);
      setEnabled(btnAddPlatoon, false);
      setEnabled(btnDeleteSelected, false);
      setEnabled(btnExportSelected, false);
      setEnabled(btnPrintSelected, false);
      if (btnExportSelected) btnExportSelected.setAttribute("href", "#");
      if (btnPrintSelected) btnPrintSelected.setAttribute("href", "#");
      return;
    }

    statusEl.textContent = "محدد: " + TYPE_LABEL[sel.type] + " — انقر مرتين لفتح الطلاب";

    setEnabled(btnAddCompany, true);
    setEnabled(btnAddPlatoon, sel.type === "company" || sel.type === "platoon");
    setEnabled(btnDeleteSelected, true);
    setEnabled(btnExportSelected, true);
    setEnabled(btnPrintSelected, true);

    if (btnExportSelected) btnExportSelected.setAttribute("href", EXPORT_URL[sel.type](sel.id));
    if (btnPrintSelected) btnPrintSelected.setAttribute("href", PRINT_URL[sel.type](sel.id));

    if (sel.type === "battalion") {
      addCompanyBattalionId.value = sel.id;
    } else if (sel.type === "company") {
      addCompanyBattalionId.value = sel.battalionId || "";
      addPlatoonCompanyId.value = sel.id;
    } else if (sel.type === "platoon") {
      addCompanyBattalionId.value = sel.battalionId || "";
      addPlatoonCompanyId.value = sel.companyId || "";
    }
  }

  /* ---- 3) نقرة واحدة: تحديد ---- */
  tree.addEventListener("click", function (e) {
    if (e.target.closest("[data-tree-toggle]")) return;
    var row = e.target.closest(".tree-row");
    if (row) selectNode(row);
  });

  /* ---- 4) نقرة مزدوجة: فتح صفحة الطلاب ---- */
  tree.addEventListener("dblclick", function (e) {
    if (e.target.closest("[data-tree-toggle]")) return;
    var row = e.target.closest(".tree-row");
    if (!row) return;
    var type = row.getAttribute("data-node-type");
    var id = row.getAttribute("data-node-id");
    if (type && id && VIEW_URL[type]) {
      window.location.href = VIEW_URL[type](id);
    }
  });

  /* ---- 5) حذف المحدد ---- */
  btnDeleteSelected.addEventListener("click", function () {
    if (!selected) return;
    deleteForm.setAttribute("action", DELETE_URL[selected.type](selected.id));
    deleteForm.dataset.confirmed = "";
    deleteForm.requestSubmit ? deleteForm.requestSubmit() : deleteForm.submit();
  });

  updatePanel(null);
})();
