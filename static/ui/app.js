(function () {
  var shell = document.getElementById("appShell");
  var sidebarToggle = document.getElementById("topbarSidebarToggle");
  if (shell && sidebarToggle) {
    sidebarToggle.addEventListener("click", function () {
      shell.classList.toggle("sidebar-hidden");
    });
  }

  var parents = document.querySelectorAll(".menu-parent[data-menu-target]");
  Array.prototype.forEach.call(parents, function (btn) {
    btn.addEventListener("click", function () {
      var target = btn.getAttribute("data-menu-target");
      if (!target) return;
      var panel = document.getElementById(target);
      if (!panel) return;
      panel.classList.toggle("open");
    });
  });
})();
