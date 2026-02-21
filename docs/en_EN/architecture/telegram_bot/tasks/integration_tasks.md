# 📋 Bot Integration Tasks

## 🛠 Feature: Commands (Welcome Screen)
- [x] Update `texts.py` with `WELCOME_USER` and `WELCOME_ADMIN`.
- [x] Update `keyboards.py` to support `is_admin` flag and `DashboardCallback`.
- [x] Update `StartOrchestrator` to check admin rights via `BotSettings`.
- [ ] **[TODO]** Update `StartOrchestrator` to parse `access_token` from `/start` payload.
- [ ] **[TODO]** Implement real `AuthDataProvider` to call Django API for user linking.

## 🛠 Feature: Bot Menu
- [ ] **[TODO]** Update `FeatureDiscoveryService` to support filtering by `is_admin`.
- [ ] **[TODO]** Ensure `BotMenuOrchestrator` only shows non-admin features.

## 🛠 Feature: Dashboard Admin (New)
- [ ] Create feature structure via `manage.py`.
- [ ] Implement `DashboardAdminOrchestrator` to show admin-only features.
- [ ] Create UI for admin statistics and system management.

## ⚙️ Core & Infrastructure
- [ ] Add `telegram_id` linking logic to the DI container.
