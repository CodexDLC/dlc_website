document.querySelectorAll('[data-item-review]').forEach(form => {
  const rows = [...form.querySelectorAll('[data-review-item]')];
  function update(focusRow) {
    const counts = {accepted: 0, rejected: 0, undecided: 0};
    rows.forEach(row => {
      const selected = row.querySelector('input[type="radio"]:checked');
      if (!row.querySelector('input[type="radio"]')) return;
      counts[selected ? selected.value : 'undecided']++;
      const area = row.querySelector('[data-review-comment]');
      if (area) {
        const rejected = selected && selected.value === 'rejected';
        area.hidden = !rejected;
        const input = area.querySelector('textarea');
        input.required = Boolean(rejected);
        if (rejected && focusRow === row) input.focus();
      }
    });
    Object.entries(counts).forEach(([key,value]) => {
      const count = form.querySelector(`[data-count="${key}"]`);
      if (count) count.textContent = value;
    });
  }
  form.addEventListener('change', event => {
    if (event.target.matches('input[type="radio"]')) update(event.target.closest('[data-review-item]'));
  });
  update();
});
