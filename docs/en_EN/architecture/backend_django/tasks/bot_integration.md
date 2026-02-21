# 📋 Django-Bot Integration Tasks

## 🗄 Models
- [ ] **[TODO]** Add `telegram_id` (BigIntegerField, unique=True) to `features.booking.models.Client`.
- [ ] **[TODO]** Create migration for `Client` model.

## 🌐 API Development
- [ ] **[TODO]** Create endpoint `POST /api/bot/link-client/` to link `telegram_id` using `access_token`.
- [ ] **[TODO]** Create endpoint `GET /api/bot/client-stats/` for `DashboardAdmin`.

## 🎨 Templates & UI
- [ ] **[TODO]** Update `step_5_success.html` (Booking) with "Connect Telegram" button.
- [ ] **[TODO]** Update Contact Form success page with "Connect Telegram" button.

## 📩 Notifications
- [ ] **[TODO]** Update `send_booking_notification_task` to include Telegram delivery if `telegram_id` is present.
