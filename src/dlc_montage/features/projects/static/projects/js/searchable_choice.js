/* Server-backed comboboxes for Anlagen and Standorte, with native select fallback. */
(() => {
  const initialized = new WeakSet();

  function selectedLabel(select) {
    const option = select.selectedOptions[0];
    return option?.value ? option.textContent.trim() : "";
  }

  function init(select) {
    if (initialized.has(select)) return;
    initialized.add(select);

    const shell = document.createElement("div");
    shell.className = "search-choice";
    const input = document.createElement("input");
    input.type = "search";
    input.autocomplete = "off";
    input.placeholder = select.dataset.searchPlaceholder || "Поиск";
    input.setAttribute("aria-label", input.placeholder);
    input.value = selectedLabel(select);
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    const results = document.createElement("div");
    results.className = "search-choice-results";
    results.setAttribute("role", "listbox");
    results.hidden = true;
    select.before(shell);
    shell.append(input, results, select);
    select.classList.add("search-choice-native");
    select.tabIndex = -1;

    let timer;
    let controller;
    let activeIndex = -1;

    function parentValue() {
      if (select.dataset.searchFixedGroup) return select.dataset.searchFixedGroup;
      const parent = select.dataset.searchParent
        ? document.querySelector(select.dataset.searchParent)
        : null;
      return parent?.value || "";
    }

    function updateAvailability() {
      if (select.dataset.searchableChoice !== "site") return true;
      const available = Boolean(parentValue());
      input.disabled = !available;
      select.disabled = !available;
      if (!available) input.value = "";
      return available;
    }

    function close() {
      results.hidden = true;
      input.setAttribute("aria-expanded", "false");
      activeIndex = -1;
    }

    function activate(index) {
      const options = [...results.querySelectorAll("button")];
      if (!options.length) return;
      activeIndex = Math.max(0, Math.min(index, options.length - 1));
      options.forEach((option, current) => option.classList.toggle("is-active", current === activeIndex));
      options[activeIndex].scrollIntoView({block: "nearest"});
    }

    function choose(item) {
      let option = [...select.options].find(candidate => candidate.value === item.value);
      if (!option) {
        option = new Option(item.label, item.value);
        select.add(option);
      }
      select.value = item.value;
      input.value = item.label;
      select.dispatchEvent(new Event("change", {bubbles: true}));
      close();
    }

    function render(items) {
      results.replaceChildren();
      items.forEach(item => {
        const button = document.createElement("button");
        button.type = "button";
        button.setAttribute("role", "option");
        const label = document.createElement("strong");
        label.textContent = item.label;
        button.append(label);
        if (item.meta) {
          const meta = document.createElement("small");
          meta.textContent = item.meta;
          button.append(meta);
        }
        button.addEventListener("mousedown", event => event.preventDefault());
        button.addEventListener("click", () => choose(item));
        results.append(button);
      });
      if (!items.length) {
        const empty = document.createElement("p");
        empty.textContent = select.dataset.searchEmpty || "Ничего не найдено";
        results.append(empty);
      }
      results.hidden = false;
      input.setAttribute("aria-expanded", "true");
      activeIndex = -1;
    }

    async function search() {
      if (!updateAvailability()) return close();
      controller?.abort();
      controller = new AbortController();
      const url = new URL(select.dataset.searchUrl, window.location.origin);
      url.searchParams.set("q", input.value.trim());
      if (select.dataset.searchableChoice === "site") url.searchParams.set("group", parentValue());
      const directionSource = select.dataset.searchDirectionSource
        ? document.querySelector(select.dataset.searchDirectionSource)
        : null;
      const direction = directionSource?.value || select.dataset.searchDirection;
      if (direction) url.searchParams.set("direction", direction);
      try {
        const response = await fetch(url, {credentials: "same-origin", signal: controller.signal});
        if (!response.ok) throw new Error("choice search failed");
        render((await response.json()).results || []);
      } catch (error) {
        if (error.name !== "AbortError") close();
      }
    }

    input.addEventListener("focus", search);
    input.addEventListener("input", () => {
      if (input.value !== selectedLabel(select) && select.value) {
        select.value = "";
        select.dispatchEvent(new Event("change", {bubbles: true}));
      }
      clearTimeout(timer);
      timer = setTimeout(search, 220);
    });
    input.addEventListener("keydown", event => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        activate(activeIndex + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        activate(activeIndex - 1);
      } else if (event.key === "Enter" && activeIndex >= 0) {
        event.preventDefault();
        results.querySelectorAll("button")[activeIndex]?.click();
      } else if (event.key === "Escape") {
        close();
      }
    });
    select.addEventListener("change", () => {
      input.value = selectedLabel(select);
      document.querySelectorAll(`[data-search-parent="#${select.id}"]`).forEach(dependent => {
        dependent.value = "";
        dependent.dispatchEvent(new Event("search-parent-change"));
      });
    });
    select.addEventListener("search-parent-change", () => {
      input.value = "";
      close();
      updateAvailability();
    });
    if (select.id) {
      input.id = `${select.id}_search`;
      document.querySelectorAll(`label[for="${select.id}"]`).forEach(label => {
        label.htmlFor = input.id;
      });
    }
    shell.addEventListener("focusout", event => {
      if (!shell.contains(event.relatedTarget)) close();
    });
    updateAvailability();
  }

  function initWithin(root = document) {
    root.querySelectorAll?.("select[data-searchable-choice]").forEach(init);
  }

  document.addEventListener("DOMContentLoaded", () => initWithin());
  document.addEventListener("htmx:afterSwap", event => initWithin(event.detail.target));
})();
