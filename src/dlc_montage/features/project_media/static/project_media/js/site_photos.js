/* Saved private photos render independently of the background source check. */
(() => {
  function start() {
    const section = document.getElementById("site-photos");
    if (!section) return;
    const gallery = section.querySelector("#site-photo-gallery");
    const toggle = section.querySelector("[data-photo-toggle]");
    const refresh = section.querySelector("[data-photo-refresh]");
    const status = section.querySelector("[data-photo-status]");
    const ru = section.dataset.language.startsWith("ru");
    const messages = ru ? {
      loading: "Загружаем сохранённые фотографии…",
      checking: "Проверяем новые фотографии в фоне…",
      ongoing: "Проверка продолжается в фоне. Позже нажмите «Проверить новые фотографии».",
      error: "Не удалось проверить фотографии. Попробуйте ещё раз.",
    } : {
      loading: "Gespeicherte Fotos werden geladen…",
      checking: "Neue Fotos werden im Hintergrund geprüft…",
      ongoing: "Die Prüfung läuft im Hintergrund weiter. Prüfen Sie neue Fotos später erneut.",
      error: "Fotos konnten nicht geprüft werden. Bitte erneut versuchen.",
    };
    const pending = new Set(["queued", "processing", "busy", "pending", "mirroring"]);
    let expanded = section.dataset.expanded === "true";
    let timer, polls = 0, stopped = false, checking = false;
    const controllers = new Set();

    function setExpanded(value) {
      expanded = value;
      section.dataset.expanded = String(value);
      gallery.hidden = !value;
      toggle.setAttribute("aria-expanded", String(value));
      toggle.textContent = value ? section.dataset.hideLabel : section.dataset.showLabel;
    }

    function merge(payload, requestedExpanded) {
      // HTML comes only from the authenticated Django fragment, with escaped names.
      const documentFragment = new DOMParser().parseFromString(payload.html, "text/html");
      const incoming = documentFragment.getElementById("site-photos");
      if (!incoming) throw new Error("Invalid gallery response");
      section.dataset.syncStatus = incoming.dataset.syncStatus || payload.status;
      for (const selector of ["[data-photo-count]", "[data-photo-badge]", "[data-photo-status]"]) {
        section.querySelector(selector).textContent = incoming.querySelector(selector).textContent;
      }
      toggle.hidden = incoming.querySelector("[data-photo-toggle]").hidden;
      section.querySelector("[data-photo-archive]").hidden = incoming.querySelector("[data-photo-archive]").hidden;
      if (requestedExpanded && expanded) {
        const existing = new Map(Array.from(gallery.children, card => [card.dataset.sitePhotoId, card]));
        const received = new Set();
        let previous = null;
        for (const card of incoming.querySelectorAll("[data-site-photo-id]")) {
          received.add(card.dataset.sitePhotoId);
          const saved = existing.get(card.dataset.sitePhotoId);
          if (saved && saved.dataset.sitePhotoVersion === card.dataset.sitePhotoVersion) {
            const currentMirror = saved.querySelector("[data-photo-mirror]");
            const incomingMirror = card.querySelector("[data-photo-mirror]");
            if (currentMirror && incomingMirror) currentMirror.textContent = incomingMirror.textContent;
          }
          const node = saved && saved.outerHTML === card.outerHTML ? saved : document.importNode(card, true);
          if (saved && node !== saved) saved.replaceWith(node);
          const next = previous ? previous.nextElementSibling : gallery.firstElementChild;
          if (next !== node) gallery.insertBefore(node, next);
          previous = node;
        }
        for (const [id, card] of existing) if (!received.has(id)) card.remove();
      }
      setExpanded(expanded);
    }

    async function request(method) {
      const controller = new AbortController();
      controllers.add(controller);
      const timeout = setTimeout(() => controller.abort(), 10000);
      const requestedExpanded = expanded;
      const url = new URL(method === "POST" ? section.dataset.refreshUrl : section.dataset.galleryUrl, location.href);
      if (requestedExpanded) url.searchParams.set("show_photos", "1");
      const headers = {Accept: "application/json"};
      if (method === "POST") {
        const token = section.querySelector("[name=csrfmiddlewaretoken]");
        headers["X-CSRFToken"] = token ? token.value : "";
      }
      try {
        const response = await fetch(url, {method, headers, credentials: "same-origin", signal: controller.signal});
        if (!response.ok || response.redirected) throw new Error("Photo request failed");
        const payload = await response.json();
        if (!stopped) merge(payload, requestedExpanded);
      } finally {
        clearTimeout(timeout);
        controllers.delete(controller);
      }
    }

    function schedule() {
      clearTimeout(timer);
      if (stopped || !pending.has(section.dataset.syncStatus)) return;
      if (polls >= 60) {
        status.textContent = messages.ongoing;
        return;
      }
      timer = setTimeout(async () => {
        polls += 1;
        try {
          await request("GET");
          schedule();
        } catch (error) {
          if (!stopped) status.textContent = messages.error;
        }
      }, 2000);
    }

    async function check() {
      if (checking || stopped) return;
      checking = true;
      clearTimeout(timer);
      polls = 0;
      refresh.disabled = true;
      status.textContent = messages.checking;
      try {
        await request("POST");
        schedule();
      } catch (error) {
        if (!stopped) status.textContent = messages.error;
      } finally {
        checking = false;
        refresh.disabled = false;
      }
    }

    toggle.addEventListener("click", async () => {
      setExpanded(!expanded);
      if (!expanded) return;
      toggle.disabled = true;
      status.textContent = messages.loading;
      try {
        await request("GET");
      } catch (error) {
        if (!stopped) status.textContent = messages.error;
      } finally {
        toggle.disabled = false;
      }
    });
    refresh.addEventListener("click", check);
    window.addEventListener("pagehide", () => {
      stopped = true;
      clearTimeout(timer);
      for (const controller of controllers) controller.abort();
    });
    window.addEventListener("pageshow", event => {
      if (event.persisted) {
        stopped = false;
        polls = 0;
        schedule();
      }
    });
    // Two frames give the rest of the cabinet a chance to paint first.
    requestAnimationFrame(() => requestAnimationFrame(check));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, {once: true});
  else start();
})();
