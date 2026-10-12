/*
 * Compiled JS — DO NOT EDIT
 * Sources: demo.js
 * Minified: False
 */


(() => {
  const form = document.querySelector('[data-demo-form]');
  if (!form) return;
  const entries = form.querySelector('[data-demo-entries]');
  const template = form.querySelector('[data-demo-empty-entry]');
  const total = form.querySelector('[name="entries-TOTAL_FORMS"]');
  const add = form.querySelector('[data-demo-add]');
  const limit = form.querySelector('[data-demo-limit]');
  if (!entries || !template || !total || !add) return;
  const max = Math.min(Number(form.querySelector('[name="entries-MAX_NUM_FORMS"]')?.value) || 100, 100);
  const update = () => {
    entries.querySelectorAll('[data-demo-entry]').forEach((entry, index) => {
      entry.querySelector('[data-entry-number]').textContent = String(index + 1);
      const deleted = entry.querySelector('[name$="-DELETE"]')?.checked;
      entry.style.opacity = deleted ? '0.6' : '';
      const output = entry.querySelector('[data-duration]');
      const start = entry.querySelector('[name$="-starts_at"]')?.value;
      const end = entry.querySelector('[name$="-ends_at"]')?.value;
      if (!start || !end || deleted) { output.textContent = ''; return; }
      const minutes = value => { const parts = value.split(':').map(Number); return parts[0] * 60 + parts[1]; };
      const duration = minutes(end) - minutes(start);
      output.textContent = duration > 0 ? `Dauer: ${(duration / 60).toLocaleString('de-DE', { maximumFractionDigits: 2 })} h` : '';
    });
    add.disabled = Number(total.value) >= max;
    limit.textContent = add.disabled ? `Maximal ${max} Positionen pro Bericht.` : '';
  };
  add.addEventListener('click', () => {
    const index = Number(total.value);
    if (!Number.isInteger(index) || index < 0 || index >= max) return;
    const fragment = template.content.cloneNode(true);
    fragment.querySelectorAll('*').forEach(element => {
      ['name', 'id', 'for'].forEach(attribute => {
        if (element.hasAttribute(attribute)) element.setAttribute(attribute, element.getAttribute(attribute).replaceAll('__prefix__', String(index)));
      });
    });
    const first = fragment.querySelector('select, input:not([type=hidden]), textarea');
    entries.append(fragment);
    total.value = String(index + 1);
    update();
    first?.focus();
  });
  form.addEventListener('input', update);
  form.addEventListener('change', update);
  update();
})();
