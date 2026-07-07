/*
 * terminal-demo.js -- demo animada del gate y/n de ErickFP (design D4,
 * spec web-landing Requirement 'Demo terminal animada del permission gate').
 *
 * Guion declarativo (SCRIPT) + motor async/await. Arranca al entrar en
 * viewport (IntersectionObserver). Botón "▶ replay" para repetir.
 * Respeta `prefers-reduced-motion`: si está activo, deja el contenido
 * estático (el que ya viene en el HTML como fallback) sin animar.
 * Si JS está deshabilitado, el <pre id="demo-output"> ya trae el texto
 * final completo -- por eso este script NUNCA borra el contenido antes de
 * confirmar que puede animar.
 */

(function () {
  "use strict";

  var SCRIPT = [
    { type: "cmd", text: "$ erickfp chat" },
    {
      type: "out",
      text:
        "ErickFP chat -- Ctrl+D o 'salir' para terminar. Escribe /help para ver los comandos disponibles.",
    },
    { type: "cmd", text: "tu> ¿qué archivos python hay en este proyecto?" },
    { type: "out", text: "[tool] bash {\"command\": \"find . -name '*.py'\"}" },
    { type: "gate", text: "¿aprobar? [y/n] › y" },
    { type: "out", text: "✓ ejecutando… 42 archivos encontrados" },
    {
      type: "out",
      text: "erickfp> Encontré 42 archivos .py, principalmente bajo src/erickfp/.",
    },
  ];

  var CHAR_DELAY_MS = 18;
  var LINE_PAUSE_MS = 260;
  var GATE_PAUSE_MS = 550;

  function sleep(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function renderStatic(el) {
    var lines = SCRIPT.map(function (step) {
      return step.text;
    });
    el.textContent = lines.join("\n");
  }

  async function playDemo(el) {
    el.textContent = "";
    for (var i = 0; i < SCRIPT.length; i++) {
      var step = SCRIPT[i];
      var lineEl = document.createElement("span");
      lineEl.className = step.type === "gate" ? "gate-line" : "";
      el.appendChild(lineEl);

      for (var c = 0; c < step.text.length; c++) {
        lineEl.textContent += step.text[c];
        // eslint-disable-next-line no-await-in-loop
        await sleep(CHAR_DELAY_MS);
      }

      el.appendChild(document.createTextNode("\n"));
      // eslint-disable-next-line no-await-in-loop
      await sleep(step.type === "gate" ? GATE_PAUSE_MS : LINE_PAUSE_MS);
    }
  }

  function initTerminalDemo() {
    var el = document.getElementById("demo-output");
    var replayBtn = document.getElementById("demo-replay");
    if (!el) return;

    if (prefersReducedMotion()) {
      // Ya viene con el estado final estático en el HTML: no lo tocamos.
      if (replayBtn) replayBtn.hidden = true;
      return;
    }

    var hasPlayed = false;
    var isPlaying = false;

    function start() {
      if (isPlaying) return;
      isPlaying = true;
      playDemo(el).then(function () {
        isPlaying = false;
      });
    }

    if ("IntersectionObserver" in window) {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting && !hasPlayed) {
              hasPlayed = true;
              start();
            }
          });
        },
        { threshold: 0.4 }
      );
      observer.observe(el);
    } else {
      // Sin soporte de IntersectionObserver: reproducir de una vez.
      start();
    }

    if (replayBtn) {
      replayBtn.addEventListener("click", function () {
        start();
      });
    }
  }

  document.addEventListener("DOMContentLoaded", initTerminalDemo);
})();
