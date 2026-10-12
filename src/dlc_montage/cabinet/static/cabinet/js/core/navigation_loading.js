/* @provides cabinet.core.navigation_loading */
(function (window, document) {
    let navigating = false;
    const requests = new Set();
    let indicator;

    function render() {
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'cab-navigation-loading';
            indicator.setAttribute('role', 'status');
            indicator.setAttribute('aria-live', 'polite');
            const text = document.createElement('span');
            text.className = 'visually-hidden';
            text.textContent = document.documentElement.lang.startsWith('de') ? 'Seite wird geladen…' : 'Страница загружается…';
            indicator.append(text);
            document.body.append(indicator);
        }
        indicator.hidden = !navigating && requests.size === 0;
    }

    function isDownload(url) {
        return /\.(?:xlsx?|csv|pdf|zip|jpe?g|png|webp)$/i.test(url.pathname)
            || /\/(?:download|excel|photos)(?:\/|$)/.test(url.pathname)
            || /\/exports\/(?:\d+|master-excel|multi-performance|work-completion|batch-settlement)\/$/.test(url.pathname);
    }

    function isPageNavigation(url) {
        return url.origin === window.location.origin
            && (url.pathname !== window.location.pathname || url.search !== window.location.search)
            && !isDownload(url);
    }

    document.addEventListener('click', event => {
        const link = event.target.closest('a[href]');
        if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey
            || link.hasAttribute('download') || (link.target && link.target !== '_self')
            || link.closest('[data-no-navigation-loading]')) return;
        const url = new URL(link.href, window.location.href);
        if (!isPageNavigation(url)) return;
        queueMicrotask(() => {
            if (!event.defaultPrevented) { navigating = true; render(); }
        });
    });

    document.addEventListener('submit', event => {
        const form = event.target;
        if (form.method === 'dialog' || (form.target && form.target !== '_self')
            || form.closest('[data-no-navigation-loading]')) return;
        const action = event.submitter?.hasAttribute('formaction') ? event.submitter.formAction : form.action;
        const url = new URL(action, window.location.href);
        if (url.origin !== window.location.origin || isDownload(url)
            || (form.method === 'post' && /\/(?:performance|final-hours)\/$/.test(url.pathname))) return;
        queueMicrotask(() => {
            if (!event.defaultPrevented) { navigating = true; render(); }
        });
    });

    document.addEventListener('htmx:beforeRequest', event => {
        queueMicrotask(() => {
            if (!event.defaultPrevented) { requests.add(event.detail.xhr); render(); }
        });
    });
    document.addEventListener('htmx:afterRequest', event => {
        requests.delete(event.detail.xhr);
        render();
    });
    window.addEventListener('pageshow', () => {
        navigating = false;
        requests.clear();
        render();
    });
    window.addEventListener('beforeunload', () => { navigating = true; render(); });
})(window, document);
