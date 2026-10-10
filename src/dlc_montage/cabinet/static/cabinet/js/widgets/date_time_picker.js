/* CODEX_DJANGO_CLI BLUEPRINT STATUS: MOVE_TO_CLI_BLUEPRINT. Reason: generated cabinet app asset source for codex-django-cli blueprints. */
/* @provides cabinet.widgets.date_time_picker
   @depends cabinet.core.dom */
(function (window) {
    window.CabinetWidgets = window.CabinetWidgets || {};
    window.CabinetWidgets.createDateTimePickerHelpers = function createDateTimePickerHelpers(config) {
        const dayMonthKeys = config.dayMonthKeys || {};
        const monthLabels = config.monthLabels || {};
        const monthKeys = config.monthKeys || [];

        return {
            isDayInCurrentMonth(iso) {
                return (dayMonthKeys[iso] || '') === this.currentMonthKey;
            },
            currentMonthLabel() {
                return monthLabels[this.currentMonthKey] || config.fallbackMonthLabel || '';
            },
            goMonth(step) {
                const index = monthKeys.indexOf(this.currentMonthKey);
                if (index === -1) return;
                const nextIndex = index + step;
                if (nextIndex < 0 || nextIndex >= monthKeys.length) return;
                this.currentMonthKey = monthKeys[nextIndex];
                if (!this.isDayInCurrentMonth(this.selectedDate)) {
                    const firstDay = Object.keys(dayMonthKeys).find((iso) => dayMonthKeys[iso] === this.currentMonthKey);
                    if (firstDay && typeof this.selectDate === 'function') {
                        this.selectDate(firstDay);
                    }
                }
            },
        };
    };
})(window);
