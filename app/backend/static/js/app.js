(function () {
  "use strict";

  const stage = document.getElementById("stage");
  const loadingTemplate = document.getElementById("loading-template");
  const introTemplate = document.getElementById("intro-template");

  function setFormError(message) {
    const el = document.getElementById("form-error");
    if (el) el.textContent = message;
  }

  function isGenerateForm(element) {
    return element && element.id === "generate-form";
  }

  // Show the loading card in the stage while a new quiz is generated.
  document.body.addEventListener("htmx:beforeRequest", function (event) {
    if (isGenerateForm(event.detail.elt) && stage && loadingTemplate) {
      stage.innerHTML = loadingTemplate.innerHTML;
      setFormError("");
    }
  });

  // Start every new stage at the top so results and fresh quizzes are not
  // hidden below the previous scroll position.
  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (!event.detail.target || event.detail.target.id !== "stage") return;
    const scroller = event.detail.target.closest(".quiz-scroll");
    if (!scroller) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    scroller.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
  });

  // Network-level failures do not get an HTML response, so restore the intro.
  function handleNetworkFailure(event) {
    if (!isGenerateForm(event.detail.elt)) return;
    if (stage && introTemplate) {
      stage.innerHTML = introTemplate.innerHTML;
    }
    setFormError("The server could not be reached. Please try again.");
  }

  document.body.addEventListener("htmx:responseError", handleNetworkFailure);
  document.body.addEventListener("htmx:sendError", handleNetworkFailure);

  // Related-topic chips fill the topic input without a round trip.
  document.body.addEventListener("click", function (event) {
    const chip = event.target.closest("[data-topic]");
    if (!chip) return;
    const input = document.getElementById("topic-input");
    if (!input) return;
    input.value = chip.getAttribute("data-topic");
    input.focus();
    setFormError("");
  });

  // Clear the topic error as soon as the user edits it.
  document.body.addEventListener("input", function (event) {
    if (event.target && event.target.id === "topic-input") {
      setFormError("");
    }
  });
})();
