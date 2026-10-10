/* Расчёт предварительного отображения. Сервер повторяет все проверки. */
(() => {
  const minutes = value => {
    if (!/^\d{2}:\d{2}$/.test(value || "")) return NaN;
    const [h, m] = value.split(":").map(Number);
    return h * 60 + m;
  };
  const label = value => {
    const editor = document.querySelector("#report-editor");
    return Number.isFinite(value) && value >= 0
      ? Math.floor(value / 60) + " " + editor.dataset.hourLabel + " "
        + String(value % 60).padStart(2, "0") + " " + editor.dataset.minuteLabel : "—";
  };
  function update() {
    const form = document.querySelector("#report-form");
    if (!form) return;
    const base = minutes(form.elements.ends_at.value) - minutes(form.elements.starts_at.value);
    const output = form.querySelector("[data-base-duration]");
    output.textContent = label(base);
    let total = 0;
    form.querySelectorAll("[data-member]").forEach(row => {
      const deduction = Number(row.querySelector('[name$="-deduction_minutes"]').value);
      const duration = base - deduction;
      row.querySelector("[data-member-total]").textContent = label(duration);
      if (row.querySelector('[name$="-employee"]').value) total += duration;
    });
    form.querySelector("[data-team-total]").textContent = label(total);
  }
  document.addEventListener("click", event => {
    const button = event.target.closest("[data-deduct]");
    if (!button) return;
    const input = button.closest("[data-member]").querySelector('[name$="-deduction_minutes"]');
    input.value = Math.max(0, Number(input.value) || 0) + Number(button.dataset.deduct);
    update();
  });
  document.addEventListener("input", event => {
    update();
  });
  document.addEventListener("change", update);
  document.addEventListener("htmx:afterSwap", update);
  document.addEventListener("htmx:responseError", () => {
    const editor = document.querySelector("#report-editor");
    if (editor) {
      const warning = document.createElement("p");
      warning.className = "time-alert";
      warning.setAttribute("role", "alert");
      warning.textContent = editor.dataset.requestError;
      editor.prepend(warning);
    }
  });
  document.addEventListener("DOMContentLoaded", update);
})();
