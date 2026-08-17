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

    const navRect = navLinks.getBoundingClientRect();
    const linkRect = link.getBoundingClientRect();

    const left = linkRect.left - navRect.left;

    indicator.style.width = `${linkRect.width}px`;
    indicator.style.transform = `translateX(${left}px)`;
    indicator.classList.add("active");
  }

  function updateActiveIndicator() {
    const activeLink =
      navLinks.querySelector(".nav-link.active") ||
      navLinks.querySelector(".nav-link[aria-current='page']");

    moveIndicator(activeLink);
  }

  links.forEach(link => {
    link.addEventListener("mouseenter", () => {
      moveIndicator(link);
    });
  });

  navLinks.addEventListener("mouseleave", updateActiveIndicator);

  window.addEventListener("resize", updateActiveIndicator);

  // Wait for fonts to finish loading before calculating positions.
  // This is important because Chrome can calculate text widths
  // differently before the web font has finished loading.
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(updateActiveIndicator);
  } else {
    updateActiveIndicator();
  }

  window.addEventListener("load", updateActiveIndicator);

  updateActiveIndicator();
})();