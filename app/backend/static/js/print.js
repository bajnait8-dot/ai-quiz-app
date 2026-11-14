(function () {
  "use strict";

  const button = document.getElementById("print-button");
  if (!button) return;

  button.addEventListener("click", function () {
    window.print();
  });
})();
