// =============================================================================
// queue_violation_shared.js — سلوك مشترك بين صفحتي «تفاصيل الطابور» و«المخالفات»:
//  1) قائمة بحث لاختيار الطالب (combobox)
//  2) إظهار/إخفاء حقل عدد الأيام حسب فئة المدة المختارة
// =============================================================================
(function () {
  "use strict";

  const students = window.__ALL_STUDENTS__ || [];
  const comboRoot = document.getElementById("studentCombo");
  if (comboRoot && window.KataebCombo) {
    window.KataebCombo(comboRoot, students);
  }

  const categorySelect = document.getElementById("durationCategorySelect");
  const daysField = document.getElementById("durationDaysField");
  const daysInput = document.getElementById("durationDaysInput");
  const daysHint = document.getElementById("durationDaysHint");

  function applyCategoryState() {
    if (!categorySelect || !daysField || !daysInput) return;
    const opt = categorySelect.options[categorySelect.selectedIndex];
    const min = opt.getAttribute("data-min");
    const max = opt.getAttribute("data-max");

    if (!min && !max) {
      // فئة "للأمر الأخير": لا حاجة لعدد أيام
      daysField.style.display = "none";
      daysInput.value = "";
      daysInput.required = false;
      daysInput.readOnly = false;
      return;
    }

    daysField.style.display = "";
    daysInput.min = min;
    daysInput.max = max;
    daysInput.required = true;

    if (min === max) {
      // فئة بيوم واحد بالضبط: نثبّت القيمة تلقائياً
      daysInput.value = min;
      daysInput.readOnly = true;
      daysHint.textContent = "مدة ثابتة: " + min + " يوم";
    } else {
      daysInput.readOnly = false;
      if (!daysInput.value || Number(daysInput.value) < Number(min) || Number(daysInput.value) > Number(max)) {
        daysInput.value = min;
      }
      daysHint.textContent = "بين " + min + " و" + max + " يوم";
    }
  }

  if (categorySelect) {
    categorySelect.addEventListener("change", applyCategoryState);
    applyCategoryState();
  }
})();
