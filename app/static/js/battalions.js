// =============================================================================
// battalions.js — شجرة الهيكل التنظيمي: طي/فتح + تحديد عنصر يتحكم بلوحة الأزرار
// =============================================================================

(function () {
  "use strict";

  const tree = document.getElementById("orgTree");
  if (!tree) return;

  /* ------------------------------------------------------------------- *
   * 1) طي/فتح الفروع
   * ------------------------------------------------------------------- */
  tree.addEventListener("click", function (e) {
    const toggleBtn = e.target.closest("[data-tree-toggle]");
    if (toggleBtn) {
      e.stopPropagation();
      const targetId = toggleBtn.getAttribute("data-tree-toggle");
      const target = document.getElementById(targetId);
      if (target) {
        target.classList.toggle("is-collapsed");
        const icon = toggleBtn.querySelector("use");
        const collapsed = target.classList.contains("is-collapsed");
        if (icon) {
          icon.setAttribute("href", collapsed ? "#icon-chevron-left" : "#icon-chevron-down");
          icon.setAttribute("xlink:href", collapsed ? "#icon-chevron-left" : "#icon-chevron-down");
        }
      }
    }
  });

  /* ------------------------------------------------------------------- *
   * 2) تحديد عنصر من الشجرة
   * ------------------------------------------------------------------- */
  const statusEl = document.getElementById("selectionStatus");
  const btnAddCompany = document.getElementById("btnAddCompany");
  const btnAddPlatoon = document.getElementById("btnAddPlatoon");
  const btnViewStudents = document.getElementById("btnViewStudents");
  const btnDeleteSelected = document.getElementById("btnDeleteSelected");
  const btnExportSelected = document.getElementById("btnExportSelected");
  const deleteForm = document.getElementById("deleteSelectedForm");
  const addCompanyBattalionId = document.getElementById("addCompanyBattalionId");
  const addPlatoonCompanyId = document.getElementById("addPlatoonCompanyId");

  const TYPE_LABEL = { battalion: "كتيبة", company: "سرية", platoon: "فصيل" };
  const VIEW_URL = {
    battalion: function (id) { return "/battalions/" + id + "/students"; },
    company: function (id) { return "/companies/" + id + "/students"; },
    platoon: function (id) { return "/platoons/" + id; },
  };
  const EXPORT_URL = {
    battalion: function (id) { return "/export/battalion/" + id; },
    company: function (id) { return "/export/company/" + id; },
    platoon: function (id) { return "/export/platoon/" + id; },
  };
  const DELETE_URL = {
    battalion: function (id) { return "/battalions/" + id + "/delete"; },
    company: function (id) { return "/companies/" + id + "/delete"; },
    platoon: function (id) { return "/platoons/" + id + "/delete"; },
  };

  let selected = null;

  function setEnabled(el, enabled) {
    if (!el) return;
    if (el.tagName === "A") {
      if (enabled) { el.style.pointerEvents = ""; el.style.opacity = ""; }
      else { el.style.pointerEvents = "none"; el.style.opacity = ".6"; }
    } else {
      el.disabled = !enabled;
    }
  }

  function clearSelectionVisual() {
    tree.querySelectorAll(".tree-row.is-selected").forEach(function (r) { r.classList.remove("is-selected"); });
  }

  function selectNode(row) {
    const type = row.getAttribute("data-node-type");
    const id = row.getAttribute("data-node-id");
    const label = row.getAttribute("data-node-label");
    const battalionId = row.getAttribute("data-battalion-id");
    const companyId = row.getAttribute("data-company-id");

    if (selected && selected.type === type && selected.id === id) {
      // النقر على نفس العنصر المحدد يلغي التحديد
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
      statusEl.textContent = "لم يتم تحديد عنصر";
      setEnabled(btnAddCompany, false);
      setEnabled(btnAddPlatoon, false);
      setEnabled(btnViewStudents, false);
      setEnabled(btnDeleteSelected, false);
      setEnabled(btnExportSelected, false);
      btnViewStudents.setAttribute("href", "#");
      btnExportSelected.setAttribute("href", "#");
      return;
    }

    statusEl.textContent = "محدد: " + TYPE_LABEL[sel.type];

    setEnabled(btnAddCompany, true);
    setEnabled(btnAddPlatoon, sel.type === "company" || sel.type === "platoon");
    setEnabled(btnViewStudents, true);
    setEnabled(btnDeleteSelected, true);
    setEnabled(btnExportSelected, true);

    btnViewStudents.setAttribute("href", VIEW_URL[sel.type](sel.id));
    btnExportSelected.setAttribute("href", EXPORT_URL[sel.type](sel.id));

    // تجهيز حقول نافذتي "إضافة سرية" و"إضافة فصيل" بحسب التحديد الحالي
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

  tree.addEventListener("click", function (e) {
    if (e.target.closest("[data-tree-toggle]")) return;
    const row = e.target.closest(".tree-row");
    if (row) selectNode(row);
  });

  btnDeleteSelected.addEventListener("click", function () {
    if (!selected) return;
    deleteForm.setAttribute("action", DELETE_URL[selected.type](selected.id));
    deleteForm.dataset.confirmed = "";
    deleteForm.requestSubmit ? deleteForm.requestSubmit() : deleteForm.submit();
  });

  updatePanel(null);

  /* ------------------------------------------------------------------- *
   * 3) فتح تلقائي لأول كتيبة إن كان العدد قليلاً (تجربة استخدام أفضل)
   * ------------------------------------------------------------------- */
  const battalionWraps = tree.querySelectorAll("[data-battalion-wrap]");
  if (battalionWraps.length && battalionWraps.length <= 3) {
    battalionWraps.forEach(function (wrap) {
      const id = wrap.getAttribute("data-battalion-wrap");
      const childrenEl = document.getElementById("b-" + id);
      // الفروع مفتوحة افتراضياً (CSS)، لا حاجة لإجراء إضافي هنا.
      void childrenEl;
    });
  }
})();
