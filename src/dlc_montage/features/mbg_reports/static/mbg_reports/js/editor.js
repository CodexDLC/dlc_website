/* Удобный выбор состава дня и предварительные строки отчёта MBG. */
(() => {
  const selectedOptions = select => [...select.options].filter(option => option.selected && option.value);
  let availabilityByEmployee = new Map();
  let availabilityReady = false;
  let availabilityController;
  let siteHistoryController;
  let workItemController;
  let focusAddedCard = false;

  function availableOptions(select) {
    const selected = new Set(selectedOptions(select).map(option => option.value));
    const options = [...select.options].filter(option => option.value && !selected.has(option.value));
    if (!select.matches("[data-entry-participants]")) return options;
    const workforce = document.querySelector("[data-day-workforce]");
    const allowed = new Set(workforce ? selectedOptions(workforce).map(option => option.value) : []);
    return options.filter(option => allowed.has(option.value));
  }

  function renderPicker(select) {
    const field = select.closest("[data-person-picker]");
    const chips = field.querySelector(".mbg-person-chips");
    const add = field.querySelector(".mbg-person-add");
    chips.replaceChildren();
    selectedOptions(select).forEach(option => {
      const chip = document.createElement("span");
      chip.className = "mbg-person-chip";
      chip.append(document.createTextNode(option.textContent));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", `${field.dataset.removeLabel}: ${option.textContent}`);
      remove.textContent = "×";
      remove.addEventListener("click", () => {
        option.selected = false;
        select.dispatchEvent(new Event("change", {bubbles: true}));
      });
      chip.append(remove);
      chips.append(chip);
    });
    add.replaceChildren(new Option(`＋ ${field.dataset.addLabel}`, ""));
    availableOptions(select).forEach(option => add.add(new Option(option.textContent, option.value)));
    add.hidden = add.options.length === 1;
  }

  function enforceWorkforce() {
    const workforce = document.querySelector("[data-day-workforce]");
    if (!workforce) return;
    const allowed = new Set(selectedOptions(workforce).map(option => option.value));
    document.querySelectorAll("[data-entry-participants]").forEach(select => {
      [...select.options].forEach(option => {
        if (option.selected && !allowed.has(option.value)) option.selected = false;
      });
    });
  }

  function initPicker(field) {
    if (field.dataset.enhanced) return;
    const select = field.querySelector("select[multiple]");
    if (!select) return;
    field.dataset.enhanced = "true";
    field.classList.add("is-enhanced");
    const picker = document.createElement("div");
    picker.className = "mbg-person-picker";
    const chips = document.createElement("div");
    chips.className = "mbg-person-chips";
    const add = document.createElement("select");
    add.className = "mbg-person-add";
    add.setAttribute("aria-label", field.dataset.addLabel);
    add.addEventListener("change", () => {
      if (!add.value) return;
      const option = [...select.options].find(item => item.value === add.value);
      if (option) option.selected = true;
      add.value = "";
      select.dispatchEvent(new Event("change", {bubbles: true}));
    });
    picker.append(chips, add);
    field.append(picker);
    renderPicker(select);
  }

  function enforceAndRenderPickers() {
    document.querySelectorAll("[data-person-picker]").forEach(initPicker);
    enforceWorkforce();
    document.querySelectorAll("[data-person-picker] select[multiple]").forEach(renderPicker);
  }

  function minutes(value) {
    if (!/^\d{2}:\d{2}$/.test(value || "")) return NaN;
    const [hours, mins] = value.split(":").map(Number);
    return hours * 60 + mins;
  }

  function personHours(start, end, people) {
    const duration = minutes(end) - minutes(start);
    if (!Number.isFinite(duration) || duration <= 0 || !people) return "—";
    return (duration * people / 60).toLocaleString(undefined, {maximumFractionDigits: 2});
  }

  function selectedText(field) {
    return field?.selectedOptions[0]?.value ? field.selectedOptions[0].textContent.trim() : "";
  }

  function fieldLabel(card, field) {
    if (!field?.id) return "";
    return card.querySelector(`label[for="${field.id}"]`)?.textContent.replace(/:\s*$/, "").trim() || "";
  }

  function workRequirements(work) {
    const option = work?.selectedOptions[0];
    return {
      route: option?.dataset.requiresRoute === "true",
      cable: option?.dataset.requiresCable === "true",
    };
  }

  function configureWorkCard(card) {
    const work = card.querySelector('[name$="-work_type"]');
    const route = card.querySelector('[name$="-route"]');
    const cable = card.querySelector('[name$="-cable_type"]');
    const requirements = workRequirements(work);
    const details = card.querySelector("[data-work-details]");
    const routeField = card.querySelector('[data-work-parameter="route"]');
    const cableField = card.querySelector('[data-work-parameter="cable"]');
    route.required = requirements.route;
    cable.required = requirements.cable;
    routeField.hidden = !requirements.route && !route.value;
    cableField.hidden = !requirements.cable && !cable.value;
    if (requirements.route || requirements.cable) details.open = true;
    return requirements;
  }

  function selectWorkItem(card) {
    const selected = card.querySelector('[name$="-work_item"]')?.selectedOptions[0];
    const delta = card.querySelector('[name$="-completed_quantity"]');
    if (!selected?.value) {
      if (delta) delta.value = "";
      return;
    }
    const fields = {
      work_type: selected.dataset.workType,
      route: selected.dataset.route,
      cable_type: selected.dataset.cableType,
    };
    Object.entries(fields).forEach(([name, value]) => {
      const field = card.querySelector(`[name$="-${name}"]`);
      if (field) field.value = value || "";
    });
    const construction = card.querySelector('[name$="-with_underconstruction"]');
    if (construction) construction.checked = selected.dataset.underconstruction === "true";
    const description = card.querySelector('[name$="-description"]');
    if (description && !description.value.trim()) description.value = selected.textContent.trim();
    configureWorkCard(card);
  }

  async function loadWorkItems(clearSelection = false) {
    const form = document.querySelector("#mbg-day-form");
    const site = form?.querySelector("[data-mbg-site]")?.value || "";
    if (!form) return;
    if (workItemController) workItemController.abort();
    if (clearSelection) {
      document.querySelectorAll('[name$="-work_item"]').forEach(select => { select.value = ""; });
      document.querySelectorAll('[name$="-completed_quantity"]').forEach(input => { input.value = ""; });
    }
    if (!site) {
      document.querySelectorAll('[name$="-work_item"]').forEach(select => {
        select.replaceChildren(new Option("---------", ""));
      });
      return;
    }
    workItemController = new AbortController();
    try {
      const response = await fetch(`${form.dataset.workItemUrl}?${new URLSearchParams({site})}`, {
        headers: {Accept: "application/json"}, signal: workItemController.signal,
      });
      if (!response.ok) throw new Error("Work items unavailable");
      const payload = await response.json();
      document.querySelectorAll('[name$="-work_item"]').forEach(select => {
        const previous = clearSelection ? "" : select.value;
        select.replaceChildren(new Option("---------", ""));
        payload.items.forEach(item => {
          const option = new Option(item.label, String(item.id));
          option.dataset.workType = String(item.work_type);
          option.dataset.route = item.route ? String(item.route) : "";
          option.dataset.cableType = item.cable_type ? String(item.cable_type) : "";
          option.dataset.underconstruction = String(item.with_underconstruction);
          select.add(option);
        });
        select.value = previous;
      });
    } catch (error) {
      if (error.name === "AbortError") return;
    }
  }

  function entryDescription(card) {
    const work = card.querySelector('[name$="-work_type"]');
    const route = card.querySelector('[name$="-route"]');
    const cable = card.querySelector('[name$="-cable_type"]');
    const quantity = card.querySelector('[name$="-quantity"]');
    const construction = card.querySelector('[name$="-with_underconstruction"]');
    const standard = card.querySelector('[name$="-standard_connections"]');
    const heavy = card.querySelector('[name$="-heavy_connections"]');
    const custom = card.querySelector('[name$="-description"]')?.value.trim();
    const requirements = configureWorkCard(card);
    const form = document.querySelector("#mbg-day-form");
    const parts = [custom || selectedText(work)].filter(Boolean);
    const routeText = selectedText(route);
    const cableText = selectedText(cable);
    if (routeText) parts.push(routeText);
    else if (requirements.route) parts.push(`(${form.dataset.chooseRoute})`);
    if (cableText) parts.push(cableText);
    else if (requirements.cable) parts.push(`(${form.dataset.chooseCable})`);
    if (construction?.checked) parts.push(fieldLabel(card, construction));
    if (Number(standard?.value) > 0) parts.push(`${fieldLabel(card, standard)}: ${standard.value}`);
    if (Number(heavy?.value) > 0) parts.push(`${fieldLabel(card, heavy)}: ${heavy.value}`);
    if (quantity?.value && Number(quantity.value) !== 1) parts.push(`× ${quantity.value}`);
    return parts.join(" · ") || "—";
  }

  function initErrorToast() {
    const toast = document.querySelector("[data-error-toast]");
    if (!toast || toast.dataset.enhanced) return;
    toast.dataset.enhanced = "true";
    toast.querySelector("[data-error-toast-close]")?.addEventListener("click", () => toast.remove());
    toast.focus({preventScroll: true});
    setTimeout(() => {
      toast.classList.add("is-hiding");
      setTimeout(() => toast.remove(), 200);
    }, 10000);
  }

  function setAvailabilityState(state) {
    const form = document.querySelector("#mbg-day-form");
    if (!form) return;
    const key = `availability${state.charAt(0).toUpperCase()}${state.slice(1)}`;
    const message = form.dataset[key] || "";
    document.querySelectorAll("[data-availability-status], [data-action-status]").forEach(element => {
      element.textContent = message;
      element.classList.toggle("is-conflict", state === "conflict");
    });
  }

  function renderAvailability(employees) {
    const form = document.querySelector("#mbg-day-form");
    const list = document.querySelector("[data-availability-list]");
    if (!form || !list) return;
    list.replaceChildren();
    employees.forEach(employee => {
      const row = document.createElement("div");
      row.className = "mbg-person-availability";
      const name = document.createElement("strong");
      name.textContent = employee.name;
      const intervals = document.createElement("div");
      if (!employee.entries.length) {
        const free = document.createElement("small");
        free.textContent = form.dataset.availabilityFree;
        intervals.append(free);
      } else {
        employee.entries.forEach(entry => {
          const interval = document.createElement("span");
          interval.className = "mbg-busy-interval";
          interval.textContent = `${entry.start}–${entry.end} · ${entry.group} · ${entry.site}`;
          intervals.append(interval);
        });
      }
      row.append(name, intervals);
      list.append(row);
    });
  }

  function overlaps(start, end, otherStart, otherEnd) {
    return start < otherEnd && end > otherStart;
  }

  function checkConflicts() {
    document.querySelectorAll("[data-work-card]").forEach(card => card.classList.remove("is-conflict"));
    if (!availabilityReady) return;
    const localByEmployee = new Map();
    let conflict = false;
    document.querySelectorAll("[data-work-card]").forEach(card => {
      const start = minutes(card.querySelector('[name$="-starts_at"]')?.value);
      const end = minutes(card.querySelector('[name$="-ends_at"]')?.value);
      const participants = card.querySelector('[name$="-participants"]');
      if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end || !participants) return;
      selectedOptions(participants).forEach(option => {
        const employeeId = option.value;
        const saved = availabilityByEmployee.get(employeeId)?.entries || [];
        if (saved.some(entry => overlaps(start, end, minutes(entry.start), minutes(entry.end)))) {
          conflict = true;
          card.classList.add("is-conflict");
        }
        const local = localByEmployee.get(employeeId) || [];
        local.forEach(interval => {
          if (overlaps(start, end, interval.start, interval.end)) {
            conflict = true;
            card.classList.add("is-conflict");
            interval.card.classList.add("is-conflict");
          }
        });
        local.push({start, end, card});
        localByEmployee.set(employeeId, local);
      });
    });
    setAvailabilityState(conflict ? "conflict" : "ready");
  }

  async function loadAvailability() {
    const form = document.querySelector("#mbg-day-form");
    const workforce = document.querySelector("[data-day-workforce]");
    const workDate = form?.querySelector('[name="work_date"]')?.value;
    if (availabilityController) availabilityController.abort();
    availabilityByEmployee = new Map();
    availabilityReady = false;
    if (!form || !workforce || !workDate || !selectedOptions(workforce).length) {
      renderAvailability([]);
      setAvailabilityState("empty");
      return;
    }
    const params = new URLSearchParams({work_date: workDate});
    selectedOptions(workforce).forEach(option => params.append("employee", option.value));
    if (form.dataset.reportId) params.set("exclude_report", form.dataset.reportId);
    availabilityController = new AbortController();
    setAvailabilityState("loading");
    try {
      const response = await fetch(`${form.dataset.availabilityUrl}?${params}`, {
        headers: {Accept: "application/json"},
        signal: availabilityController.signal,
      });
      if (!response.ok) throw new Error("Availability request failed");
      const payload = await response.json();
      availabilityByEmployee = new Map(payload.employees.map(employee => [String(employee.id), employee]));
      availabilityReady = true;
      renderAvailability(payload.employees);
      checkConflicts();
    } catch (error) {
      if (error.name === "AbortError") return;
      renderAvailability([]);
      setAvailabilityState("error");
    }
  }

  async function loadSiteHistory() {
    const form = document.querySelector("#mbg-day-form");
    const panel = document.querySelector("[data-site-history]");
    const site = form?.querySelector("[data-mbg-site]")?.value || "";
    if (!form || !panel || panel.dataset.loadedSite === site) return;
    if (siteHistoryController) siteHistoryController.abort();
    siteHistoryController = new AbortController();
    panel.classList.add("is-loading");
    const params = new URLSearchParams({site});
    if (form.dataset.reportId) params.set("exclude_report", form.dataset.reportId);
    try {
      const response = await fetch(`${form.dataset.siteHistoryUrl}?${params}`, {
        headers: {"HX-Request": "true"},
        signal: siteHistoryController.signal,
      });
      if (!response.ok) throw new Error("Site history request failed");
      panel.outerHTML = await response.text();
    } catch (error) {
      if (error.name === "AbortError") return;
      panel.classList.remove("is-loading");
      const empty = panel.querySelector(".mbg-site-history-empty");
      if (empty) empty.textContent = form.dataset.siteHistoryError;
    }
  }

  function renderSummary() {
    const body = document.querySelector("[data-work-summary-body]");
    if (!body) return;
    body.replaceChildren();
    document.querySelectorAll("[data-work-card]").forEach(card => {
      const work = card.querySelector('[name$="-work_type"]');
      const start = card.querySelector('[name$="-starts_at"]');
      const end = card.querySelector('[name$="-ends_at"]');
      const participants = card.querySelector('[name$="-participants"]');
      const people = selectedOptions(participants);
      if (!work.value && !start.value && !end.value && !people.length) return;
      const row = body.insertRow();
      row.insertCell().textContent = `${start.value || "—"}–${end.value || "—"}`;
      row.insertCell().textContent = entryDescription(card);
      row.insertCell().textContent = people.map(option => option.textContent).join(", ");
      row.insertCell().textContent = personHours(start.value, end.value, people.length);
    });
    document.querySelector("[data-work-summary-empty]").hidden = body.rows.length > 0;
    checkConflicts();
  }

  function update() {
    initErrorToast();
    enforceAndRenderPickers();
    renderSummary();
    loadAvailability();
    loadSiteHistory();
    loadWorkItems();
    if (focusAddedCard) {
      focusAddedCard = false;
      const cards = document.querySelectorAll("[data-work-card]");
      const card = cards[cards.length - 1];
      card?.scrollIntoView({behavior: "smooth", block: "center"});
      card?.querySelector('[name$="-work_type"]')?.focus({preventScroll: true});
    }
  }

  document.addEventListener("click", event => {
    if (event.target.closest('[data-mbg-action-bar] button[value="add"]')) focusAddedCard = true;
  });
  document.addEventListener("change", event => {
    if (event.target.matches("[data-day-workforce], [data-entry-participants]")) enforceAndRenderPickers();
    if (event.target.matches("[data-day-workforce], [name=work_date]")) loadAvailability();
    if (event.target.matches("[data-mbg-site]")) {
      loadSiteHistory();
      loadWorkItems(true);
    }
    if (event.target.matches("[data-work-item]")) selectWorkItem(event.target.closest("[data-work-card]"));
    renderSummary();
  });
  document.addEventListener("input", renderSummary);
  document.addEventListener("htmx:afterSwap", update);
  document.addEventListener("DOMContentLoaded", update);
})();
