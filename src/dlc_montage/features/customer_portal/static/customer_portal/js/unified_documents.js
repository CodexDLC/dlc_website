/**
 * DLC Montage Unified Documents Presentation JS
 * Unobtrusive UI enhancements for tabs, batch selection, and paid rows filter.
 * Strict rule: ZERO network requests or auto-submit on page load.
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Tab switching for Internal Admin
  const tabButtons = document.querySelectorAll("[data-unified-tab]");
  const tabPanels = document.querySelectorAll("[data-unified-tab-panel]");

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetPanelId = button.getAttribute("data-unified-tab");

      tabButtons.forEach((btn) => {
        btn.setAttribute("aria-selected", "false");
        btn.classList.remove("is-active");
      });
      tabPanels.forEach((panel) => {
        panel.hidden = true;
      });

      button.setAttribute("aria-selected", "true");
      button.classList.add("is-active");

      const activePanel = document.getElementById(targetPanelId);
      if (activePanel) {
        activePanel.hidden = false;
      }
    });
  });

  // 2. Batch selection for "Отчёт для выставления счёта" (chosen sites)
  const batchForm = document.querySelector("[data-batch-settlement-form]");
  const submitBtn = document.querySelector("[data-batch-submit-btn]");
  if (batchForm || submitBtn) {
    const checkboxes = document.querySelectorAll(".unified-site-select-cb:not([disabled])");
    const selectAllCbs = document.querySelectorAll("[data-select-all-sites]");

    const updateSubmitState = () => {
      const activeCheckboxes = document.querySelectorAll(".unified-site-select-cb:not([disabled])");
      const checkedCount = Array.from(activeCheckboxes).filter((cb) => cb.checked).length;
      if (submitBtn) {
        submitBtn.disabled = checkedCount === 0;
        const baseLabel = submitBtn.getAttribute("data-base-label");
        submitBtn.textContent = checkedCount > 0 ? `${baseLabel} (${checkedCount})` : baseLabel;
      }
    };

    checkboxes.forEach((cb) => {
      cb.addEventListener("change", updateSubmitState);
    });

    selectAllCbs.forEach((allCb) => {
      allCb.addEventListener("change", () => {
        const groupContainer = allCb.closest("[data-doc-group]");
        const groupCbs = groupContainer
          ? groupContainer.querySelectorAll(".unified-site-select-cb:not([disabled])")
          : document.querySelectorAll(".unified-site-select-cb:not([disabled])");
        groupCbs.forEach((cb) => {
          cb.checked = allCb.checked;
        });
        updateSubmitState();
      });
    });

    updateSubmitState();
  }

  // 3. "Включить оплаченные" toggle enables/disables paid checkboxes while archive stays viewable
  const includePaidCb = document.querySelector("[data-filter-include-paid]");
  if (includePaidCb) {
    const paidCheckboxes = document.querySelectorAll(".is-paid-cb");

    const updatePaidCheckboxesState = () => {
      const isAllowed = includePaidCb.checked;
      paidCheckboxes.forEach((cb) => {
        cb.disabled = !isAllowed;
        if (!isAllowed) {
          cb.checked = false;
          cb.title = includePaidCb.dataset.paidExcludedTitle;
        } else {
          cb.title = includePaidCb.dataset.paidIncludedTitle;
        }
      });
      // Re-trigger update of batch submit state
      const activeCheckboxes = document.querySelectorAll(".unified-site-select-cb:not([disabled])");
      const checkedCount = Array.from(activeCheckboxes).filter((cb) => cb.checked).length;
      if (submitBtn) {
        submitBtn.disabled = checkedCount === 0;
        const baseLabel = submitBtn.getAttribute("data-base-label");
        submitBtn.textContent = checkedCount > 0 ? `${baseLabel} (${checkedCount})` : baseLabel;
      }
    };

    includePaidCb.addEventListener("change", updatePaidCheckboxesState);
    updatePaidCheckboxesState();
  }
});
