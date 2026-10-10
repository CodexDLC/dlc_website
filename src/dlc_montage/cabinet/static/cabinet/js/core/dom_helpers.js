/* CODEX_DJANGO_CLI BLUEPRINT STATUS: MOVE_TO_CLI_BLUEPRINT. Reason: generated cabinet app asset source for codex-django-cli blueprints. */
/* @provides cabinet.core.dom */
(function (window) {
    window.CabinetCore = window.CabinetCore || {};

    window.CabinetCore.ensureNamespace = function ensureNamespace(path) {
        const parts = path.split('.');
        let cursor = window;
        parts.forEach((part) => {
            cursor[part] = cursor[part] || {};
            cursor = cursor[part];
        });
        return cursor;
    };
})(window);
