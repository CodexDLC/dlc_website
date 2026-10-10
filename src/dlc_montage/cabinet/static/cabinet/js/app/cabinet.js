/*
 * Compiled JS — DO NOT EDIT
 * Sources: core/dom_helpers.js, core/htmx_csrf.js, core/sidebar_sync.js, widgets/client_lookup.js, widgets/date_time_picker.js, widgets/tabbed_assignment.js, app/cabinet.entry.js
 * Minified: False
 */




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





(function (window, document) {
    document.addEventListener('htmx:configRequest', function (evt) {
        const method = evt.detail.verb.toUpperCase();
        if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
            const token = document.cookie.match(/csrftoken=([^;]+)/);
            if (token) {
                evt.detail.headers['X-CSRFToken'] = token[1];
            }
        }
    });
})(window, document);





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





(function (window) {
    function normalizeClient(client) {
        return {
            id: client?.id || null,
            name: client?.name || '',
            phone: client?.phone || '',
            email: client?.email || '',
            fname: client?.fname || '',
            lname: client?.lname || '',
            visits: client?.visits || 0,
        };
    }

    function splitName(fullName) {
        const parts = (fullName || '').trim().split(/\s+/).filter(Boolean);
        return {
            fname: parts[0] || '',
            lname: parts.slice(1).join(' ') || '',
        };
    }

    window.CabinetWidgets = window.CabinetWidgets || {};
    window.CabinetWidgets.createClientLookup = function createClientLookup(config) {
        return {
            search: '',
            selectedId: null,
            selectedName: '',
            clientFName: '',
            clientLName: '',
            clientPhone: '',
            clientEmail: '',
            clients: config.clients || [],
            minSearchLength: config.minSearchLength || 3,

            get filteredClients() {
                if (this.search.trim().length < this.minSearchLength) {
                    return [];
                }
                const query = this.search.trim().toLowerCase();
                return this.clients.filter((client) => {
                    return client.name.toLowerCase().includes(query)
                        || client.phone.includes(this.search.trim())
                        || (client.email || '').toLowerCase().includes(query);
                });
            },

            selectClient(client) {
                const normalized = normalizeClient(client);
                this.selectedId = normalized.id;
                this.selectedName = normalized.name;
                this.search = normalized.name;
                if (!normalized.fname && normalized.name) {
                    const split = splitName(normalized.name);
                    normalized.fname = split.fname;
                    normalized.lname = split.lname;
                }
                this.clientFName = normalized.fname;
                this.clientLName = normalized.lname;
                this.clientPhone = normalized.phone;
                this.clientEmail = normalized.email;
                this.$dispatch('client-selected', normalized.id ? normalized : null);
                this.syncToParent();
            },

            confirmNewClient() {
                if (!this.clientFName.trim()) {
                    return;
                }
                const newClient = {
                    id: 'new-' + Date.now(),
                    name: (this.clientFName + ' ' + this.clientLName).trim(),
                    phone: this.clientPhone,
                    email: this.clientEmail,
                    fname: this.clientFName,
                    lname: this.clientLName,
                    isNew: true,
                };
                this.selectClient(newClient);
            },

            quickAdd() {
                if (!this.search.trim()) {
                    return;
                }
                const split = splitName(this.search);
                this.clientFName = split.fname;
                this.clientLName = split.lname;
                this.syncToParent();
                this.confirmNewClient();
            },

            syncToParent() {
                this.$dispatch('client-input', {
                    fname: this.clientFName,
                    lname: this.clientLName,
                    phone: this.clientPhone,
                    email: this.clientEmail,
                });
            },

            clearSelection() {
                this.selectedId = null;
                this.selectedName = '';
                this.search = '';
                this.clientFName = '';
                this.clientLName = '';
                this.clientPhone = '';
                this.clientEmail = '';
                this.$dispatch('client-selected', null);
                this.syncToParent();
            },

            hydrateFromExternal(client) {
                if (!client) {
                    this.selectedId = null;
                    this.selectedName = '';
                    this.search = '';
                    this.clientFName = '';
                    this.clientLName = '';
                    this.clientPhone = '';
                    this.clientEmail = '';
                    return;
                }
                if (client.id === this.selectedId) {
                    return;
                }
                this.selectedId = client.id || null;
                this.selectedName = client.name || '';
                this.search = client.name || '';
                this.clientFName = client.fname || splitName(client.name).fname;
                this.clientLName = client.lname || splitName(client.name).lname;
                this.clientPhone = client.phone || '';
                this.clientEmail = client.email || '';
            },
        };
    };

    window.cabinetClientLookup = function cabinetClientLookup(config) {
        return window.CabinetWidgets.createClientLookup(config);
    };
})(window);





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





(function () {
    
})();
