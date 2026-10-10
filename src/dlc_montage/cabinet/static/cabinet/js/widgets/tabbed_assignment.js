/* CODEX_DJANGO_CLI BLUEPRINT STATUS: MOVE_TO_CLI_BLUEPRINT. Reason: generated cabinet app asset source for codex-django-cli blueprints. */
/* @provides cabinet.widgets.tabbed_assignment
   @depends cabinet.core.dom */
(function (window) {
    window.CabinetWidgets = window.CabinetWidgets || {};
    window.CabinetWidgets.createTabbedAssignment = function createTabbedAssignment(config) {
        return {
            activeKey: config.activeKey || '',
            switchTab(nextKey) {
                this.activeKey = nextKey;
                if (typeof config.onSwitch === 'function') {
                    config.onSwitch.call(this, nextKey);
                }
            },
        };
    };
})(window);
