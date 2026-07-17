// =============================================================================
// students_view.js — حفظ الملاحظات تلقائياً + تصفية جدول الطلاب لحظياً
// (يخدم شاشة عرض/إدارة الطلاب الموحّدة على مستوى فصيل/سرية/كتيبة)
// =============================================================================
(function () {
  "use strict";

  document.querySelectorAll("[data-student-notes]").forEach(function (input) {
    let timer = null;
    let lastSaved = input.value;

    function save() {
      if (input.value === lastSaved) return;
      const studentId = input.getAttribute("data-student-notes");
      const body = new URLSearchParams();
      body.set("notes", input.value);
      fetch("/students/" + studentId + "/notes", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
      })
        .then(function (r) { return r.json(); })
        .then(function () {
          lastSaved = input.value;
          flashSaved(input);
        })
        .catch(function () { /* تجاهل بصمت: ستُحفظ عند إعادة المحاولة */ });
    }

    function flashSaved(el) {
      const prevBorder = el.style.borderColor;
      el.style.borderColor = "#15803d";
      setTimeout(function () { el.style.borderColor = prevBorder; }, 700);
    }

    input.addEventListener("blur", save);
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(save, 1200);
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); input.blur(); }
    });
  });

  const filterInput = document.getElementById("studentsFilter");
  const table = document.getElementById("studentsTable");
  if (filterInput && table) {
    filterInput.addEventListener("input", function () {
      const q = filterInput.value.trim().toLowerCase();
      table.querySelectorAll("tbody tr").forEach(function (row) {
        const haystack = (row.getAttribute("data-row-search") || "").toLowerCase();
        row.style.display = !q || haystack.indexOf(q) !== -1 ? "" : "none";
      });
    });
  }
})();
