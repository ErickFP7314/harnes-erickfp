/*
 * main.js -- comportamiento compartido de WebPage/: nav toggle (mobile),
 * scrollspy (IntersectionObserver, prefijo "> " en el link activo),
 * reveal-on-scroll, tabs accesibles, y copy-to-clipboard.
 * Design: landing-webpage D5. Reutilizado también por guia.html (spec
 * web-guia Requirement 'Coherencia con la landing').
 *
 * Sin dependencias externas. Vanilla JS.
 */

(function () {
  "use strict";

  /* ---------- Nav toggle (mobile) ---------- */
  function initNavToggle() {
    var toggle = document.getElementById("nav-toggle");
    var links = document.getElementById("nav-links");
    if (!toggle || !links) return;

    toggle.addEventListener("click", function () {
      var isOpen = links.getAttribute("data-open") === "true";
      links.setAttribute("data-open", String(!isOpen));
      toggle.setAttribute("aria-expanded", String(!isOpen));
    });

    links.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        links.setAttribute("data-open", "false");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* ---------- Scrollspy: prefijo "> " en el link de sección activa ---------- */
  function initScrollspy() {
    var navLinks = Array.prototype.slice.call(
      document.querySelectorAll("[data-nav]")
    );
    if (!navLinks.length || !("IntersectionObserver" in window)) return;

    var sectionsByLink = navLinks
      .map(function (link) {
        var id = (link.getAttribute("href") || "").replace("#", "");
        var section = id ? document.getElementById(id) : null;
        if (!section) return null;
        link.dataset.originalText = link.textContent;
        return { link: link, section: section };
      })
      .filter(Boolean);

    function setActive(link) {
      navLinks.forEach(function (l) {
        l.removeAttribute("data-active");
        l.textContent = l.dataset.originalText || l.textContent;
      });
      link.setAttribute("data-active", "true");
      link.textContent = "> " + (link.dataset.originalText || link.textContent);
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var match = sectionsByLink.find(function (pair) {
            return pair.section === entry.target;
          });
          if (match) setActive(match.link);
        });
      },
      { rootMargin: "-40% 0px -50% 0px", threshold: 0 }
    );

    sectionsByLink.forEach(function (pair) {
      observer.observe(pair.section);
    });
  }

  /* ---------- Reveal-on-scroll ---------- */
  function initReveal() {
    var revealEls = document.querySelectorAll(".reveal");
    if (!revealEls.length) return;

    if (!("IntersectionObserver" in window)) {
      revealEls.forEach(function (el) {
        el.classList.add("visible");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );

    revealEls.forEach(function (el) {
      observer.observe(el);
    });
  }

  /* ---------- Tabs accesibles (instalación) ---------- */
  function initTabs() {
    document.querySelectorAll("[data-tabs]").forEach(function (wrapper) {
      var tabs = Array.prototype.slice.call(
        wrapper.querySelectorAll('[role="tab"]')
      );
      if (!tabs.length) return;

      function activate(tab) {
        tabs.forEach(function (t) {
          var panel = document.getElementById(t.getAttribute("aria-controls"));
          var isActive = t === tab;
          t.setAttribute("aria-selected", String(isActive));
          t.tabIndex = isActive ? 0 : -1;
          if (panel) panel.hidden = !isActive;
        });
        tab.focus();
      }

      tabs.forEach(function (tab, index) {
        tab.addEventListener("click", function () {
          activate(tab);
        });
        tab.addEventListener("keydown", function (event) {
          var newIndex = null;
          if (event.key === "ArrowRight") newIndex = (index + 1) % tabs.length;
          if (event.key === "ArrowLeft")
            newIndex = (index - 1 + tabs.length) % tabs.length;
          if (newIndex !== null) {
            event.preventDefault();
            activate(tabs[newIndex]);
          }
        });
      });
    });
  }

  /* ---------- Copy-to-clipboard ---------- */
  function initCopyButtons() {
    document.querySelectorAll(".copy-btn[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var text = btn.getAttribute("data-copy") || "";
        var originalLabel = btn.textContent;

        function markCopied() {
          btn.dataset.copied = "true";
          btn.textContent = "¡Copiado!";
          setTimeout(function () {
            btn.dataset.copied = "false";
            btn.textContent = originalLabel;
          }, 1600);
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(markCopied, function () {
            fallbackCopy(text);
            markCopied();
          });
        } else {
          fallbackCopy(text);
          markCopied();
        }
      });
    });
  }

  function fallbackCopy(text) {
    var textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "absolute";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
    } catch (err) {
      /* silencioso: navegador sin soporte, el usuario puede seleccionar manualmente */
    }
    document.body.removeChild(textarea);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initNavToggle();
    initScrollspy();
    initReveal();
    initTabs();
    initCopyButtons();
  });
})();
