(function () {
  var KEYWORDS = ["SELECT", "FROM", "JOIN", "ON", "WHERE", "GROUP BY", "ORDER BY", "WITH",
    "AS", "OVER", "PARTITION BY", "DESC", "ASC", "ROWS BETWEEN", "PRECEDING", "CURRENT ROW",
    "IS NOT NULL", "AND", "OR", "IN"];
  var FUNCS = ["RANK", "ROUND", "SUM", "LAG", "AVG", "strftime"];

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function highlight(raw) {
    var sortedKeywords = KEYWORDS.slice().sort(function (a, b) { return b.length - a.length; });
    return raw.split("\n").map(function (line) {
      var commentIdx = line.indexOf("--");
      var code = commentIdx >= 0 ? line.slice(0, commentIdx) : line;
      var comment = commentIdx >= 0 ? line.slice(commentIdx) : "";

      code = esc(code);

      FUNCS.forEach(function (fn) {
        var re = new RegExp("\\b(" + fn + ")\\b", "g");
        code = code.replace(re, '<span class="tok-fn">$1</span>');
      });
      sortedKeywords.forEach(function (kw) {
        var re = new RegExp("\\b(" + kw.replace(/ /g, "\\s+") + ")\\b", "gi");
        code = code.replace(re, '<span class="tok-kw">$1</span>');
      });
      code = code.replace(/\b(\d+(\.\d+)?)\b/g, '<span class="tok-num">$1</span>');

      if (comment) {
        code += '<span class="tok-cm">' + esc(comment) + "</span>";
      }
      return code;
    }).join("\n");
  }

  function initHighlighting() {
    document.querySelectorAll("pre.sql-code[data-sql], pre.py-code[data-sql]").forEach(function (el) {
      if (el.dataset.highlighted) return;
      el.dataset.raw = el.textContent;
      el.innerHTML = highlight(el.textContent);
      el.dataset.highlighted = "1";
    });
  }

  function initCopyButtons() {
    document.querySelectorAll(".copy-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var target = document.getElementById(btn.getAttribute("data-copy-target"));
        if (!target) return;
        var text = target.dataset.raw || target.textContent;
        navigator.clipboard.writeText(text).then(function () {
          var original = btn.textContent;
          btn.textContent = "Copied";
          btn.classList.add("copied");
          setTimeout(function () {
            btn.textContent = original;
            btn.classList.remove("copied");
          }, 1600);
        });
      });
    });
  }

  function initTabs() {
    document.querySelectorAll("[data-tabs]").forEach(function (group) {
      var buttons = group.querySelectorAll(".tab-btn");
      var panels = group.querySelectorAll(".tab-panel");
      buttons.forEach(function (btn) {
        btn.addEventListener("click", function () {
          buttons.forEach(function (b) { b.classList.remove("active"); });
          panels.forEach(function (p) { p.classList.remove("active"); });
          btn.classList.add("active");
          var target = group.querySelector('.tab-panel[data-panel="' + btn.dataset.tab + '"]');
          if (target) target.classList.add("active");
        });
      });
    });
  }

  function initSortableTables() {
    document.querySelectorAll("table.sortable").forEach(function (table) {
      var tbody = table.querySelector("tbody");
      var headers = table.querySelectorAll("thead th");
      headers.forEach(function (th, colIndex) {
        th.addEventListener("click", function () {
          var currentDir = th.getAttribute("data-dir");
          var nextDir = currentDir === "asc" ? "desc" : "asc";
          headers.forEach(function (h) { h.removeAttribute("data-dir"); });
          th.setAttribute("data-dir", nextDir);

          var isNum = th.classList.contains("num");
          var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));

          rows.sort(function (a, b) {
            var av = a.children[colIndex].getAttribute("data-value") || a.children[colIndex].textContent;
            var bv = b.children[colIndex].getAttribute("data-value") || b.children[colIndex].textContent;
            if (isNum) {
              av = parseFloat(av); bv = parseFloat(bv);
              return nextDir === "asc" ? av - bv : bv - av;
            }
            return nextDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
          });

          rows.forEach(function (r) { tbody.appendChild(r); });
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initHighlighting();
    initCopyButtons();
    initTabs();
    initSortableTables();
  });
})();
