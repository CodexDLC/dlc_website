/* CODEX_DJANGO_CLI BLUEPRINT STATUS: MOVE_TO_CLI_BLUEPRINT. Reason: generated cabinet app asset source for codex-django-cli blueprints. */
/* @provides cabinet.core.sidebar_sync
   @depends cabinet.core.dom */
(function (window, document) {
    function syncSidebarLinks() {
        const currentPath = window.location.pathname;
        const currentSearch = window.location.search;
        const fullUrl = currentPath + currentSearch;

        document.querySelectorAll('#cab-sidebar .cab-nav__item').forEach((link) => {
            const href = link.getAttribute('href');
            if (!href) {
                return;
            }

            let isMatch = false;
            if (href.includes('?')) {
                isMatch = fullUrl.includes(href);
            } else if (href !== '/') {
                isMatch = currentPath === href || currentPath === href + '/';
            }

            link.classList.toggle('active', isMatch);
        });
    }

    window.CabinetCore = window.CabinetCore || {};
    window.CabinetCore.syncSidebarLinks = syncSidebarLinks;

    document.body.addEventListener('htmx:afterSettle', syncSidebarLinks);
    document.addEventListener('DOMContentLoaded', syncSidebarLinks);
    window.addEventListener('popstate', syncSidebarLinks);
})(window, document);
