(() => {
  "use strict";

  const root = document.querySelector("[data-export-picker]");
  if (!root) return;

  const picker = root.querySelector("#custom-zwischen-picker");
  const form = root.querySelector("#custom-zwischen-form");
  const groupSelect = root.querySelector("#group-picker-select");
  const emptyNotice = root.querySelector("#selected-groups-empty");
  const submitBar = root.querySelector("#custom-export-submit-bar");

  const groupCards = () => Array.from(root.querySelectorAll(".selected-group-card"));

  const updateSelectionState = () => {
    const hasVisibleCards = groupCards().some((card) => !card.hidden);
    emptyNotice.hidden = hasVisibleCards;
    submitBar.hidden = !hasVisibleCards;
  };

  const setGroupSelected = (groupId, selected) => {
    const card = root.querySelector(`#group-card-${groupId}`);
    if (!card) return;

    card.hidden = !selected;
    card.querySelectorAll(".site-picker-cb").forEach((checkbox) => {
      checkbox.disabled = !selected;
      checkbox.checked = selected;
    });
    const groupToggle = card.querySelector(".group-picker-toggle");
    if (groupToggle) groupToggle.checked = selected;

    const option = root.querySelector(`#opt-group-${groupId}`);
    if (option) option.disabled = selected;
    updateSelectionState();
  };

  root.addEventListener("click", (event) => {
    const actionButton = event.target.closest("[data-action]");
    if (!actionButton || !root.contains(actionButton)) return;

    const action = actionButton.dataset.action;
    if (action === "toggle-picker") {
      picker.hidden = !picker.hidden;
      actionButton.setAttribute("aria-expanded", String(!picker.hidden));
    } else if (action === "add-group") {
      if (!groupSelect.value) return;
      setGroupSelected(groupSelect.value, true);
      groupSelect.value = "";
    } else if (action === "remove-group") {
      setGroupSelected(actionButton.dataset.groupId, false);
    } else if (action === "add-all-groups") {
      groupCards().forEach((card) => setGroupSelected(card.dataset.groupId, true));
      groupSelect.value = "";
    } else if (action === "remove-all-groups") {
      groupCards().forEach((card) => setGroupSelected(card.dataset.groupId, false));
    }
  });

  root.addEventListener("change", (event) => {
    if (!event.target.matches(".group-picker-toggle")) return;
    event.target.closest(".selected-group-card").querySelectorAll(".site-picker-cb").forEach((checkbox) => {
      checkbox.checked = event.target.checked;
    });
  });

  form.addEventListener("submit", (event) => {
    if (form.querySelector(".site-picker-cb:checked")) return;
    event.preventDefault();
    window.alert(form.dataset.emptySelectionMessage);
  });

  updateSelectionState();
})();
