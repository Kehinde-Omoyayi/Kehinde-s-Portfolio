(function () {
  "use strict";

  const navLinks = document.querySelector(".nav-links");
  const indicator = document.querySelector(".nav-links-indicator");

  if (!navLinks || !indicator) return;

  const links = navLinks.querySelectorAll(".nav-link");

  function moveIndicator(link) {
    if (!link) {
      indicator.classList.remove("active");
      return;
    }

    const linkRect = link.getBoundingClientRect();
    const wrapperRect = indicator.parentElement.getBoundingClientRect();

    const left = linkRect.left - wrapperRect.left;

    indicator.style.left = `${left}px`;
    indicator.style.width = `${linkRect.width}px`;
    indicator.classList.add("active");
  }

  function getActiveLink() {
    return (
      navLinks.querySelector(".nav-link.active") ||
      navLinks.querySelector(".nav-link[aria-current='page']")
    );
  }

  function updateIndicator() {
    moveIndicator(getActiveLink());
  }

  links.forEach(function (link) {
    link.addEventListener("mouseenter", function () {
      moveIndicator(this);
    });
  });

  navLinks.addEventListener("mouseleave", function () {
    updateIndicator();
  });

  window.addEventListener("resize", updateIndicator);

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(updateIndicator);
  }

  window.addEventListener("load", updateIndicator);

  updateIndicator();
})();