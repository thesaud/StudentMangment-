// =============================================================================
// app.js — سلوكيات عامة مشتركة عبر كل الصفحات
// (تنبيهات تختفي تلقائياً، نافذة تأكيد قبل الحذف، نوافذ منبثقة، قوائم بحث)
// =============================================================================

(function () {
  "use strict";

  /* ---------------------------------------------------------------------
   * 1) التنبيهات (Flash messages): إغلاق يدوي + اختفاء تلقائي
   * ------------------------------------------------------------------- */
  document.querySelectorAll(".alert[data-flash]").forEach(function (alertEl) {
    const closeBtn = alertEl.querySelector(".alert-close");
    if (closeBtn) closeBtn.addEventListener("click", function () { dismiss(alertEl); });
    setTimeout(function () { dismiss(alertEl); }, 6000);
  });

  function dismiss(el) {
    if (!el || el.dataset.dismissed) return;
    el.dataset.dismissed = "1";
    el.style.transition = "opacity .25s ease, transform .25s ease";
    el.style.opacity = "0";
    el.style.transform = "translateY(-6px)";
    setTimeout(function () { el.remove(); }, 250);
  }

  /* ---------------------------------------------------------------------
   * 2) نافذة تأكيد عامة (بدلاً من confirm() الافتراضية للمتصفح)
   *    الاستخدام: <form data-confirm="نص السؤال" data-confirm-label="تأكيد الحذف">
   * ------------------------------------------------------------------- */
  let confirmOverlay = null;

  function buildConfirmModal() {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML =
      '<div class="modal-box" role="alertdialog" aria-modal="true">' +
        '<div class="modal-title danger">' +
          '<span data-confirm-title>تأكيد الإجراء</span>' +
          '<button type="button" class="modal-close-x" data-confirm-cancel aria-label="إغلاق">' +
            '<svg><use href="#icon-x" xlink:href="#icon-x"/></svg>' +
          "</button>" +
        "</div>" +
        '<p data-confirm-text style="color:var(--text-mid); font-size:14px; line-height:1.7; margin:0;"></p>' +
        '<div class="modal-actions">' +
          '<button type="button" class="btn btn-outline" data-confirm-cancel>تراجع</button>' +
          '<button type="button" class="btn btn-red" data-confirm-ok></button>' +
        "</div>" +
      "</div>";
    document.body.appendChild(overlay);
    return overlay;
  }

  function openConfirm(text, okLabel) {
    if (!confirmOverlay) confirmOverlay = buildConfirmModal();
    confirmOverlay.querySelector("[data-confirm-text]").textContent = text;
    const okBtn = confirmOverlay.querySelector("[data-confirm-ok]");
    okBtn.textContent = okLabel || "تأكيد";
    confirmOverlay.classList.add("is-open");
    return new Promise(function (resolve) {
      function cleanup(result) {
        confirmOverlay.classList.remove("is-open");
        okBtn.removeEventListener("click", onOk);
        confirmOverlay.querySelectorAll("[data-confirm-cancel]").forEach(function (b) {
          b.removeEventListener("click", onCancel);
        });
        resolve(result);
      }
      function onOk() { cleanup(true); }
      function onCancel() { cleanup(false); }
      okBtn.addEventListener("click", onOk);
      confirmOverlay.querySelectorAll("[data-confirm-cancel]").forEach(function (b) {
        b.addEventListener("click", onCancel);
      });
    });
  }

  document.addEventListener("submit", function (e) {
    const form = e.target;
    if (!(form instanceof HTMLElement)) return;
    if (!form.hasAttribute("data-confirm")) return;
    if (form.dataset.confirmed === "1") return;
    e.preventDefault();
    const text = form.getAttribute("data-confirm");
    const label = form.getAttribute("data-confirm-label") || "تأكيد";
    openConfirm(text, label).then(function (ok) {
      if (ok) {
        form.dataset.confirmed = "1";
        form.requestSubmit ? form.requestSubmit() : form.submit();
      }
    });
  });

  /* ---------------------------------------------------------------------
   * 3) نوافذ منبثقة عامة (data-modal-open="id" / data-modal-close)
   * ------------------------------------------------------------------- */
  document.addEventListener("click", function (e) {
    const opener = e.target.closest("[data-modal-open]");
    if (opener) {
      const id = opener.getAttribute("data-modal-open");
      const modal = document.getElementById(id);
      if (modal) {
        modal.classList.add("is-open");
        const autofocus = modal.querySelector("[autofocus]");
        if (autofocus) setTimeout(function () { autofocus.focus(); }, 30);
      }
    }
    const closer = e.target.closest("[data-modal-close]");
    if (closer) {
      const overlay = closer.closest(".modal-overlay");
      if (overlay) overlay.classList.remove("is-open");
    }
    if (e.target.classList && e.target.classList.contains("modal-overlay")) {
      e.target.classList.remove("is-open");
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-overlay.is-open").forEach(function (m) { m.classList.remove("is-open"); });
    }
  });

  /* ---------------------------------------------------------------------
   * 4) قائمة بحث قابلة للاختيار (combobox) لاختيار طالب من قائمة كبيرة
   *    data: [{sid, sname, national_id, phone, pname, cname, bname}, ...]
   * ------------------------------------------------------------------- */
  window.KataebCombo = function (root, items, onSelect) {
    const input = root.querySelector("[data-combo-input]");
    const hidden = root.querySelector("[data-combo-value]");
    const results = root.querySelector("[data-combo-results]");
    if (!input || !results) return;

    function render(list) {
      if (!list.length) {
        results.innerHTML = '<div class="combo-option"><span class="text-faint">لا توجد نتائج مطابقة</span></div>';
        return;
      }
      results.innerHTML = list.slice(0, 40).map(function (s) {
        return (
          '<button type="button" class="combo-option" data-sid="' + s.sid + '">' +
            '<div>' + escapeHtml(s.sname) + "</div>" +
            '<div class="sub">' + escapeHtml(s.bname) + " / " + escapeHtml(s.cname) + " / " + escapeHtml(s.pname) +
            (s.national_id ? " · هوية: " + escapeHtml(s.national_id) : "") +
            "</div>" +
          "</button>"
        );
      }).join("");
    }

    function escapeHtml(str) {
      return String(str == null ? "" : str).replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
    }

    function filter(q) {
      q = (q || "").trim().toLowerCase();
      if (!q) return items.slice(0, 40);
      return items.filter(function (s) {
        return (
          (s.sname || "").toLowerCase().indexOf(q) !== -1 ||
          (s.national_id || "").toLowerCase().indexOf(q) !== -1 ||
          (s.phone || "").toLowerCase().indexOf(q) !== -1 ||
          (s.pname || "").toLowerCase().indexOf(q) !== -1 ||
          (s.cname || "").toLowerCase().indexOf(q) !== -1 ||
          (s.bname || "").toLowerCase().indexOf(q) !== -1
        );
      });
    }

    input.addEventListener("focus", function () {
      render(filter(input.value));
      results.classList.add("is-open");
    });
    input.addEventListener("input", function () {
      render(filter(input.value));
      results.classList.add("is-open");
      if (hidden) hidden.value = "";
    });
    document.addEventListener("click", function (e) {
      if (!root.contains(e.target)) results.classList.remove("is-open");
    });
    results.addEventListener("click", function (e) {
      const opt = e.target.closest(".combo-option[data-sid]");
      if (!opt) return;
      const sid = opt.getAttribute("data-sid");
      const item = items.find(function (s) { return String(s.sid) === String(sid); });
      if (!item) return;
      input.value = item.sname;
      if (hidden) hidden.value = item.sid;
      results.classList.remove("is-open");
      if (typeof onSelect === "function") onSelect(item);
    });
  };

  /* ---------------------------------------------------------------------
   * 5) قوائم متتالية عامة (كتيبة -> سرية -> فصيل) عبر /api/companies/<id>
   *    و /api/platoons/<id>. الاستخدام: يضع كل عنصر <select> سمة
   *    data-cascade="battalion|company|platoon" ضمن حاوية واحدة data-cascade-group.
   * ------------------------------------------------------------------- */
  function fillSelect(select, items, placeholder) {
    select.innerHTML = "";
    if (!items.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = placeholder || "لا يوجد";
      select.appendChild(opt);
      return;
    }
    items.forEach(function (item) {
      const opt = document.createElement("option");
      opt.value = item.id;
      opt.textContent = item.name;
      select.appendChild(opt);
    });
  }

  document.querySelectorAll("[data-cascade-group]").forEach(function (group) {
    const battalionSel = group.querySelector('[data-cascade="battalion"]');
    const companySel = group.querySelector('[data-cascade="company"]');
    const platoonSel = group.querySelector('[data-cascade="platoon"]');
    if (!battalionSel || !companySel || !platoonSel) return;

    function loadCompanies(battalionId, thenLoadPlatoons) {
      fetch("/api/companies/" + battalionId).then(function (r) { return r.json(); }).then(function (items) {
        fillSelect(companySel, items, "لا توجد سرايا");
        if (thenLoadPlatoons && companySel.value) loadPlatoons(companySel.value);
        else if (thenLoadPlatoons) fillSelect(platoonSel, [], "لا توجد فصائل");
      });
    }
    function loadPlatoons(companyId) {
      fetch("/api/platoons/" + companyId).then(function (r) { return r.json(); }).then(function (items) {
        fillSelect(platoonSel, items, "لا توجد فصائل");
      });
    }

    battalionSel.addEventListener("change", function () { loadCompanies(battalionSel.value, true); });
    companySel.addEventListener("change", function () { loadPlatoons(companySel.value); });
  });
})();
