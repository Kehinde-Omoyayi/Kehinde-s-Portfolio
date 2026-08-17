/* Animates and auto-dismisses the centered Django-messages popup rendered
 * by partials/messages_popup.html. Shared by the public site and Studio.
 * Runs immediately (this script tag sits right after the markup it
 * targets), so there's no DOMContentLoaded race with the toast nodes. */
(function () {
  "use strict";

  var root = document.getElementById("lmPopupRoot");
  if (!root) return;

  var toasts = Array.prototype.slice.call(root.querySelectorAll(".lm-popup-toast"));
  if (!toasts.length) return;

  var VISIBLE_MS = 3000;
  var LEAVE_MS = 450;
  var STAGGER_MS = 70;

  // Start each toast hidden, then let it transition in — this only
  // happens when JS actually runs, so the no-JS fallback (CSS-visible
  // by default) is unaffected.
  toasts.forEach(function (toast) {
    toast.classList.add("lm-popup-enter");
  });

  // Force a reflow so the browser registers the "enter" state before we
  // remove it, otherwise the transition can get skipped.
  void root.offsetWidth;

  requestAnimationFrame(function () {
    toasts.forEach(function (toast, i) {
      setTimeout(function () {
        toast.classList.remove("lm-popup-enter");
        toast.classList.add("lm-popup-visible");
      }, i * STAGGER_MS);
    });
  });

  setTimeout(function () {
    toasts.forEach(function (toast) {
      toast.classList.remove("lm-popup-visible");
      toast.classList.add("lm-popup-leaving");
    });
    setTimeout(function () {
      if (root.parentNode) root.parentNode.removeChild(root);
    }, LEAVE_MS);
  }, VISIBLE_MS);
})();
