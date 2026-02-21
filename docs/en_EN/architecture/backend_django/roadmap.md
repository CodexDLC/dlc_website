# 🗺️ Django Backend Development Roadmap

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

---

This roadmap organizes development tasks by **domain** (feature area). It reflects the current state of the project after the implementation of the core booking system.

## 📊 Overall Progress

| Domain | Status | Progress | Priority |
|:---|:---:|:---:|:---:|
| **[✅ Booking System Core](#-booking-system-core)** | ✅ Done | 100% | Critical |
| **[✅ Booking Wizard UI (HTMX)](#-booking-wizard-ui-htmx)** | ✅ Done | 100% | Critical |
| **[📝 Notifications & Background Tasks](#-notifications--background-tasks)** | 🔄 In Progress | 20% | High |
| **[📝 Telegram Bot Integration](#-telegram-bot-integration)** | 📝 Ready | 0% | High |
| **[🔐 QR Finalization (Future)](#-qr-finalization-future)** | 📝 Design | 5% | Medium |
| **[🎨 Frontend & Design](#-frontend--design)** | ✅ Done | 90% | Critical |
| **[📄 Content Pages](#-content-pages)** | ✅ Done | 95% | Critical |
| **[🌐 Localization (i18n)](#-localization-i18n)** | 🔄 In Progress | 40% | High |
| **[🔍 SEO & Analytics](#-seo--analytics)** | 🔄 In Progress | 30% | High |
| **[⚙️ Admin & Backend](#️-admin--backend)** | 🔄 In Progress | 60% | Medium |

---

## ✅ Booking System Core

**Goal:** Solid foundation with Master, Client (Ghost), and Appointment models.
**Status:** ✅ 100% - Core models and services are implemented and in use.

### Tasks
- [x] **[TASK-101](./tasks/TASK-101-master-model.md):** Create `Master` model.
- [x] **[TASK-301](./tasks/TASK-301-client-model.md):** Create `Client` model with Ghost User pattern.
- [x] **[TASK-201](./tasks/TASK-201-appointment-model.md):** Create `Appointment` model.
- [x] Implement `ClientService` for ghost user management.
- [x] Implement `BookingService` for appointment creation.
- [x] Refactor services to be stateless and use static methods.
- [x] Optimize database queries in services (e.g., using `Q` objects).

---

## ✅ Booking Wizard UI (HTMX)

**Goal:** Dynamic, multi-step booking flow for a seamless user experience.
**Status:** ✅ 100% - The booking wizard is fully functional.

### Tasks
- [x] **[TASK-204](./tasks/TASK-204-htmx-booking-flow.md):** Implement HTMX-based wizard.
- [x] Implement `BookingState` DTO for type-safe session management.
- [x] Implement `BookingSessionService` to handle the DTO.
- [x] Refactor view, steps, and selectors to use the `BookingState` DTO.
- [x] Support Service-first booking path.
- [x] Ensure the flow is responsive and works on mobile.

---

## 📝 Notifications & Background Tasks

**Goal:** Inform users and admins about booking status via Email and background tasks.
**Status:** 20% - Basic structure exists. Background tasks (ARQ) are not implemented.

### Tasks
- [ ] **[ARQ]** Implement ARQ client for asynchronous task processing.
- [ ] **[ARQ]** Create a background task for sending booking confirmation emails.
- [ ] **[ARQ]** Create a background task for sending appointment reminders (e.g., 24 hours before).
- [x] **[Email]** Basic email notification functions exist in `services/notifications.py`.
- [ ] Create and translate all required email templates (`booking_approved`, `booking_rejected`, etc.).

---

## 📝 Telegram Bot Integration

**Goal:** Connect Django booking system with a Telegram Bot for admin and client interactions.
**Status:** 0% - Not implemented. Requires a dedicated API and bot-side logic.

### Tasks
- [ ] **[TASK-501]** Create a REST API for the bot (e.g., using Django Ninja).
- [ ] **[TASK-502]** Implement bot authentication (e.g., shared secret or token).
- [ ] **[TASK-503]** Expose booking endpoints (`/api/bot/book`, `/api/bot/cancel`).
- [ ] **[TASK-504]** Sync Client records between the bot and Django.
- [ ] **[TASK-506]** Add `telegram_id` field to Client and Master models.
- [ ] Implement bot-side logic for handling user interactions.

---

## 🔐 QR Finalization (Future)

**Goal:** On-site appointment finalization via QR scanning by masters.
**Status:** 5% - Full design documented, implementation is a future feature.

### Tasks
- [ ] **[TASK-205](./tasks/TASK-205-qr-finalization-system.md):** Implement the full QR finalization system.
- [ ] Develop a Telegram Bot Mini App with a QR scanner.
- [ ] Implement API endpoints for scan validation and finalization.
- [ ] Implement lead tracking for unauthorized scans.

---
## 📄 Content Pages

**Goal:** All essential pages with SEO optimization.
**Status:** 95% - Main pages are done, some content/translations may be pending.

### Tasks
- [x] Home page, Services overview, Service detail pages.
- [x] Team page (owner + masters list).
- [x] Legal pages (Impressum, Datenschutz).
- [x] Error pages (404, 500).
- [ ] Contacts page with map and contact form.
- [ ] Complete all translations.

---
## 🎨 Frontend & Design

**Goal:** Professional, responsive design ready for production.
**Status:** 90% - Core CSS and structure are complete. Minor JS tweaks and optimizations may be needed.

### Tasks
- [x] Modular CSS structure and compilation system.
- [x] 5-breakpoint responsive system.
- [x] WebP image conversion.
- [x] Base layout with header/footer.
- [ ] Add mobile menu toggle (burger menu).
- [ ] Image lazy loading.
- [ ] Optimize Lighthouse scores (Performance 90+).

---
## 🌐 Localization (i18n)

**Goal:** Full 4-language support (DE, RU, UK, EN).
**Status:** 40% - Technical setup is done, content translation is in progress.

### Tasks
- [x] Configure `django-modeltranslation`.
- [x] Add translation tags to templates.
- [ ] **[TASK-401]** Translate all static text.
- [ ] **[TASK-402]** Add language switcher to header.
- [ ] **[TASK-403]** Configure URL localization (`/de/`, `/ru/`, etc.).

---
## 🔍 SEO & Analytics

**Goal:** Optimize for search engines and implement tracking.
**Status:** 30% - Basic SEO structure is in place.

### Tasks
- [x] Add SEO meta tags to templates via mixins.
- [x] Create `sitemap.xml` and `robots.txt`.
- [ ] **[TASK-601]** Add JSON-LD structured data (e.g., `BeautySalon` schema).
- [ ] **[TASK-603]** Add Google Analytics / Matomo.

---
## ⚙️ Admin & Backend

**Goal:** Efficient admin interface for content management.
**Status:** 60% - Basic admin for core models is configured. Advanced features are pending.

### Tasks
- [x] Configure Django Admin with custom styling.
- [x] Add admin for `Category`, `Service`, `Master`, `Client`, `Appointment`.
- [x] Use `modeltranslation` in admin.
- [ ] **[TASK-701]** Customize admin dashboard with statistics.
- [ ] **[TASK-703]** Implement image upload previews.
- [ ] **[TASK-704]** Add inline editing for related models.
