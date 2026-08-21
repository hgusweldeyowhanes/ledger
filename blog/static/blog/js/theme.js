(function () {
  var root = document.documentElement;
  var btn = document.getElementById("theme-toggle");
  function apply(theme) {
    root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("ledger-theme", theme);
    } catch (e) {}
    if (btn) {
      btn.textContent = theme === "light" ? "Dark" : "Light";
    }
  }
  var current = root.getAttribute("data-theme") || "dark";
  apply(current);
  if (btn) {
    btn.addEventListener("click", function () {
      apply(root.getAttribute("data-theme") === "light" ? "dark" : "light");
    });
  }
})();
