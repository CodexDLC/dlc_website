/* Закрытый просмотр фотографий и PDF в кабинете. */
(() => {
  const dialog = document.querySelector("[data-media-dialog]");
  if (!dialog) return;
  const title = dialog.querySelector("[data-media-dialog-title]");
  const image = dialog.querySelector("[data-media-dialog-image]");
  const pdf = dialog.querySelector("[data-media-dialog-pdf]");

  function resetPreview() {
    image.hidden = true;
    image.removeAttribute("src");
    image.alt = "";
    pdf.hidden = true;
    pdf.removeAttribute("src");
  }

  function openPreview(trigger) {
    resetPreview();
    title.textContent = trigger.dataset.previewTitle;
    if (trigger.dataset.previewKind === "image") {
      image.src = trigger.dataset.previewUrl;
      image.alt = trigger.dataset.previewTitle;
      image.hidden = false;
    } else {
      pdf.src = trigger.dataset.previewUrl;
      pdf.hidden = false;
    }
    dialog.showModal();
  }

  document.addEventListener("click", event => {
    const trigger = event.target.closest("[data-media-preview]");
    if (trigger) openPreview(trigger);
    if (event.target.closest("[data-media-close]")) dialog.close();
  });
  dialog.addEventListener("click", event => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", resetPreview);
})();
