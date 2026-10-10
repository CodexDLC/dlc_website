/* CODEX_DJANGO_CLI BLUEPRINT STATUS: MOVE_TO_CLI_BLUEPRINT. Reason: generated cabinet app asset source for codex-django-cli blueprints. */
/* @provides cabinet.widgets.client_lookup
   @depends cabinet.core.dom */
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
