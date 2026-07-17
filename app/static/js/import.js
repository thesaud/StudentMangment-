// =============================================================================
// import.js — سلوك صفحة «الاستيراد والتوزيع التلقائي»
//  1) منطقة السحب/الإفلات لملف الإكسل + عرض اسم الملف المختار
//  2) توليد حقول "عدد فصائل كل سرية" ديناميكياً حسب عدد السرايا
//     (كل سرية يمكن أن يكون لها عدد فصائل مختلف — متطلب جديد)
//  3) حساب إجمالي الفصائل الناتجة لحظياً
//  4) تفعيل زر «تنفيذ التوزيع الآن» فقط بعد تأشير مربع التأكيد
// =============================================================================
(function () {
  "use strict";

  /* ---- منطقة رفع الملف ---- */
  const fileInput = document.getElementById("excelFileInput");
  const fileDrop = document.getElementById("fileDrop");
  const fileNameBox = document.getElementById("fileDropFilename");

  if (fileInput && fileDrop) {
    fileInput.addEventListener("change", function () {
      if (fileInput.files && fileInput.files[0]) {
        fileNameBox.textContent = "📄 " + fileInput.files[0].name;
        fileNameBox.style.display = "inline-flex";
      }
    });
    ["dragenter", "dragover"].forEach(function (evt) {
      fileDrop.addEventListener(evt, function (e) {
        e.preventDefault();
        fileDrop.classList.add("dragover");
      });
    });
    ["dragleave", "drop"].forEach(function (evt) {
      fileDrop.addEventListener(evt, function (e) {
        e.preventDefault();
        fileDrop.classList.remove("dragover");
      });
    });
    fileDrop.addEventListener("drop", function (e) {
      const files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length) {
        fileInput.files = files;
        fileNameBox.textContent = "📄 " + files[0].name;
        fileNameBox.style.display = "inline-flex";
      }
    });
  }

  /* ---- حقول عدد الفصائل لكل سرية (ديناميكية) ---- */
  const bInput = document.getElementById("battalionCountInput");
  const cInput = document.getElementById("companiesCountInput");
  const grid = document.getElementById("platoonCountsGrid");
  const totalOut = document.getElementById("totalPlatoonsPreview");

  function currentPlatoonCounts() {
    if (!grid) return [];
    return Array.from(grid.querySelectorAll('input[name="platoon_counts"]'))
      .map(function (el) { return parseInt(el.value, 10) || 0; });
  }

  function updateTotal() {
    if (!totalOut) return;
    const b = bInput ? (parseInt(bInput.value, 10) || 0) : 0;
    const counts = currentPlatoonCounts();
    const sum = counts.reduce(function (a, x) { return a + x; }, 0);
    if (b > 0 && counts.length && counts.every(function (x) { return x > 0; })) {
      totalOut.textContent = (b * sum) + " فصيل (" + counts.length + " سرية × " + b + " كتيبة)";
    } else {
      totalOut.textContent = "—";
    }
  }

  function rebuildPlatoonInputs() {
    if (!grid || !cInput) return;
    const wanted = Math.max(0, Math.min(24, parseInt(cInput.value, 10) || 0));
    const existing = currentPlatoonCounts();

    grid.innerHTML = "";
    for (let i = 0; i < wanted; i++) {
      const field = document.createElement("div");
      field.className = "field";
      const label = document.createElement("label");
      label.className = "field-label";
      label.textContent = "السرية " + (i + 1);
      const input = document.createElement("input");
      input.type = "number";
      input.name = "platoon_counts";
      input.className = "field-input";
      input.min = "1";
      input.required = true;
      input.value = existing[i] > 0 ? existing[i] : 4;
      input.addEventListener("input", updateTotal);
      field.appendChild(label);
      field.appendChild(input);
      grid.appendChild(field);
    }
    updateTotal();
  }

  if (grid && cInput) {
    // قيم ابتدائية (عند العودة من خطوة المراجعة تحمل القيم السابقة)
    const initial = (grid.getAttribute("data-initial-counts") || "")
      .split(",").map(function (s) { return parseInt(s, 10); })
      .filter(function (n) { return n > 0; });
    if (initial.length) {
      cInput.value = initial.length;
      rebuildPlatoonInputs();
      const inputs = grid.querySelectorAll('input[name="platoon_counts"]');
      initial.forEach(function (v, i) { if (inputs[i]) inputs[i].value = v; });
      updateTotal();
    } else {
      rebuildPlatoonInputs();
    }
    cInput.addEventListener("input", rebuildPlatoonInputs);
  }
  if (bInput) bInput.addEventListener("input", updateTotal);

  /* ---- تفعيل زر التنفيذ فقط بعد التأشير على مربع التأكيد ---- */
  const confirmCheckbox = document.getElementById("confirmWipeCheckbox");
  const confirmBtn = document.getElementById("confirmDistributeBtn");
  if (confirmCheckbox && confirmBtn) {
    confirmCheckbox.addEventListener("change", function () {
      confirmBtn.disabled = !confirmCheckbox.checked;
    });
  }
})();
