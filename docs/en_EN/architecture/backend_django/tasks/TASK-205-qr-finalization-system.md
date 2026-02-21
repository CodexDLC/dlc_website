# TASK-205: QR Finalization System with Lead Tracking

**Status:** 📝 Future Feature (Post-MVP)
**Priority:** High (after MVP launch)
**Domain:** Booking System (Advanced)
**Estimate:** 16-20 hours

---

## Description

Implement advanced QR-based appointment finalization where:
1. Client receives QR code after booking (email/SMS)
2. Master scans client's QR via Telegram Bot Mini App
3. Master enters actual price → appointment finalized
4. Unauthorized scans are tracked as potential leads

**This replaces manual confirmation with automated, secure, on-site finalization.**

## Prerequisites

Before implementing this task:
- [ ] TASK-MVP-001 completed (basic booking works)
- [ ] TASK-101 completed (Master model exists)
- [ ] TASK-301 completed (Client model with Ghost User)
- [ ] TASK-201 completed (Appointment model)
- [ ] Telegram Bot infrastructure ready
- [ ] Email/SMS sending configured

## Acceptance Criteria

- [ ] `Appointment.finalize_token` field added
- [ ] `Master.telegram_id` and `Master.qr_token` fields
- [ ] QR code generation on booking confirmation
- [ ] Telegram Bot Mini App with QR scanner (HTML5)
- [ ] API endpoint for QR validation and finalization
- [ ] Security: only correct master can finalize
- [ ] `ScanAttempt` model for analytics
- [ ] `PotentialLead` model for unauthorized scans
- [ ] Price adjustment UI (preset buttons + custom input)
- [ ] Client notification after finalization

## Technical Details

### 1. Models Extension

```python
# features/booking/models/appointment.py (extend existing)
class Appointment(models.Model):
    ...

    # QR Finalization
    finalize_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False
    )

    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        'Master',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='finalized_appointments'
    )

    def can_be_finalized_by(self, master):
        return (
            self.master_id == master.id and
            self.status == self.STATUS_CONFIRMED and
            self.is_today and
            not self.finalized_at
        )


# features/booking/models/master.py (extend existing)
class Master(models.Model):
    ...

    # Telegram Integration
    telegram_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        db_index=True
    )

    bot_access_code = models.CharField(
        max_length=8,
        unique=True,
        editable=False
    )


# features/booking/models/scan_attempt.py (new)
class ScanAttempt(TimestampMixin):
    """Analytics: who scanned which QR code"""
    appointment = models.ForeignKey('Appointment', on_delete=models.CASCADE)
    scanned_by_master = models.ForeignKey('Master', null=True, on_delete=models.SET_NULL)
    telegram_id = models.BigIntegerField(null=True, blank=True)
    scan_type = models.CharField(max_length=30)  # success, wrong_master, unauthorized


# features/booking/models/potential_lead.py (new)
class PotentialLead(TimestampMixin):
    """Potential clients from various sources"""
    telegram_id = models.BigIntegerField(null=True, db_index=True)
    source = models.CharField(max_length=30)  # qr_scan_unauthorized, website, etc.
    notes = models.TextField(blank=True)
    converted_to_client = models.ForeignKey('Client', null=True, on_delete=models.SET_NULL)
```

### 2. QR Code Generation

```python
# features/booking/services/qr_generation.py
import qrcode
from io import BytesIO

def generate_appointment_qr(appointment):
    """Generate QR code for appointment"""
    qr_url = f"https://t.me/lily_bot?start=finalize_{appointment.finalize_token}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#003831", back_color="#EDD071")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return buffer
```

### 3. Telegram Bot Mini App (QR Scanner)

```html
<!-- telegram_bot/webapp/qr-scanner.html -->
<!DOCTYPE html>
<html>
<head>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
            background: var(--tg-theme-bg-color);
            color: var(--tg-theme-text-color);
        }
        #qr-reader {
            width: 100%;
            border-radius: 12px;
            overflow: hidden;
        }
        .status {
            margin-top: 20px;
            text-align: center;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <h2>📷 QR-Code scannen</h2>
    <div id="qr-reader"></div>
    <div class="status" id="status">Kamera wird geladen...</div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        function onScanSuccess(decodedText) {
            // Extract token from URL
            const token = decodedText.split('finalize_')[1];

            if (!token) {
                document.getElementById('status').innerText = '❌ Ungültiger QR-Code';
                return;
            }

            // Send to 02_telegram_bot
            tg.sendData(JSON.stringify({
                action: 'finalize_appointment',
                token: token
            }));

            tg.close();
        }

        function onScanError(errorMessage) {
            // Ignore scan errors (too noisy)
        }

        // Start scanner
        const html5QrCode = new Html5Qrcode("qr-reader");

        html5QrCode.start(
            { facingMode: "environment" },  // Back camera
            { fps: 10, qrbox: 250 },
            onScanSuccess,
            onScanError
        ).then(() => {
            document.getElementById('status').innerText = '✅ Bereit zum Scannen';
        }).catch(err => {
            document.getElementById('status').innerText = '❌ Kamera-Zugriff verweigert';
        });
    </script>
</body>
</html>
```

### 4. Bot Handler (Master Scans QR)

```python
# telegram_bot/features/master_panel/handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import httpx
import json

router = Router()

@router.message(Command("scan"))
async def open_scanner(message: Message):
    """Open QR scanner Mini App"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📷 Kamera öffnen",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/qr-scanner.html")
        )]
    ])

    await message.answer(
        "📸 Scannen Sie den QR-Code des Kunden:",
        reply_markup=keyboard
    )


@router.message(F.web_app_data)
async def handle_qr_scan(message: Message):
    """Process scanned QR code"""
    data = json.loads(message.web_app_data.data)

    if data['action'] != 'finalize_appointment':
        return

    finalize_token = data['token']
    master_telegram_id = message.from_user.id

    # Validate with Django API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DJANGO_API_URL}/api/02_telegram_bot/appointment/scan/",
            params={
                "finalize_token": finalize_token,
                "master_telegram_id": master_telegram_id,
                "telegram_username": message.from_user.username or ""
            }
        )

    # Handle different scenarios
    if response.status_code == 404:
        await message.answer("❌ Ungültiger QR-Code")
        return

    elif response.status_code == 403:
        error = response.json()

        if error['error'] == 'not_master':
            # Unauthorized person - save as lead!
            await message.answer(
                "⚠️ Sie sind nicht als Meister registriert.\n\n"
                "💡 Möchten Sie einen Termin buchen?\n"
                "Nutzen Sie /book"
            )

        elif error['error'] == 'wrong_master':
            # Wrong master - analytics recorded
            await message.answer(
                f"❌ Dies ist ein Termin bei {error['correct_master']}.\n\n"
                f"Sie können diesen nicht abschließen."
            )

        return

    # Success - show finalization form
    apt = response.json()['appointment']

    price_min = int(apt['price_min'])
    price_max = int(apt['price_max']) if apt['price_max'] else price_min + 30
    prices = [price_min, price_min + 10, price_min + 20, price_max]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{p}€", callback_data=f"fin:{finalize_token}:{p}")
            for p in prices[:2]
        ],
        [
            InlineKeyboardButton(text=f"{p}€", callback_data=f"fin:{finalize_token}:{p}")
            for p in prices[2:]
        ],
        [
            InlineKeyboardButton(text="✏️ Andere Summe", callback_data=f"fin_custom:{finalize_token}")
        ]
    ])

    await message.answer(
        f"✅ <b>Termin gefunden!</b>\n\n"
        f"👤 {apt['client_name']}\n"
        f"💅 {apt['service_title']}\n"
        f"⏰ {apt['datetime_start'][11:16]} Uhr\n"
        f"💰 Orientierung: {apt['price_quoted']}€\n\n"
        f"<b>Endpreis angeben:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("fin:"))
async def finalize_appointment(callback: CallbackQuery):
    """Finalize with selected price"""
    _, finalize_token, price = callback.data.split(":")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DJANGO_API_URL}/api/02_telegram_bot/appointment/finalize/",
            json={
                "finalize_token": finalize_token,
                "actual_price": float(price),
                "master_telegram_id": callback.from_user.id
            }
        )

    if response.status_code == 200:
        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ <b>Abgeschlossen!</b>\nBetrag: {price}€",
            parse_mode="HTML"
        )
        await callback.answer("✅ Termin abgeschlossen")
    else:
        await callback.answer("❌ Fehler", show_alert=True)
```

### 5. Django API (Scan & Finalize)

```python
# features/booking/api/finalization.py
from ninja import Router
from django.shortcuts import get_object_or_404
from features.booking.models import Appointment, Master, ScanAttempt, PotentialLead

api = Router()

@api.get("/appointment/scan/")
def scan_qr(request, finalize_token: str, master_telegram_id: int, telegram_username: str = ''):
    """Validate QR scan"""
    try:
        apt = Appointment.objects.get(finalize_token=finalize_token)
    except Appointment.DoesNotExist:
        return {"error": "invalid_qr"}, 404

    # Find master
    try:
        master = Master.objects.get(telegram_id=master_telegram_id)
    except Master.DoesNotExist:
        # Not a master - save as lead
        PotentialLead.objects.create(
            telegram_id=master_telegram_id,
            telegram_username=telegram_username,
            source='qr_scan_unauthorized',
            notes=f'Scanned appointment #{apt.id}'
        )
        return {"error": "not_master"}, 403

    # Check if correct master
    if not apt.can_be_finalized_by(master):
        ScanAttempt.objects.create(
            appointment=apt,
            scanned_by_master=master,
            telegram_id=master_telegram_id,
            scan_type='wrong_master'
        )
        return {
            "error": "wrong_master",
            "correct_master": apt.master.name
        }, 403

    # Success
    ScanAttempt.objects.create(
        appointment=apt,
        scanned_by_master=master,
        scan_type='success'
    )

    return {
        "appointment": {
            "client_name": apt.client.display_name(),
            "service_title": apt.service.title,
            "datetime_start": apt.datetime_start.isoformat(),
            "price_quoted": float(apt.price_quoted),
            "price_min": float(apt.service.price_min),
            "price_max": float(apt.service.price_max) if apt.service.price_max else None,
        }
    }


@api.post("/appointment/finalize/")
def finalize(request, finalize_token: str, actual_price: float, master_telegram_id: int):
    """Finalize appointment"""
    apt = get_object_or_404(Appointment, finalize_token=finalize_token)
    master = get_object_or_404(Master, telegram_id=master_telegram_id)

    if not apt.can_be_finalized_by(master):
        return {"error": "Cannot finalize"}, 403

    apt.price_actual = actual_price
    apt.status = Appointment.STATUS_COMPLETED
    apt.finalized_at = timezone.now()
    apt.finalized_by = master
    apt.save()

    return {"success": True}
```

## Security Features

✅ **Only registered masters** can scan (Master.telegram_id check)
✅ **Only correct master** can finalize (Appointment.master_id validation)
✅ **Unauthorized scans** tracked as leads (PotentialLead created)
✅ **Wrong master scans** logged (ScanAttempt analytics)
✅ **One-time finalization** (finalized_at prevents duplicates)
✅ **Time-based validation** (only today's appointments)

## Analytics Dashboard

Add to Django Admin:
- Scan attempts by type (success, unauthorized, wrong_master)
- Conversion rate: leads → clients
- Master activity (who finalizes most appointments)
- Average price deviation (quoted vs actual)

## Dependencies

- **Requires:** Telegram Bot with Mini Apps support
- **Requires:** HTTPS for Mini App hosting
- **Requires:** QR code library (`pip install qrcode[pil]`)
- **Requires:** HTML5-QRCode library (CDN or self-hosted)

## Future Enhancements

- [ ] Offline QR scanning (PWA cache)
- [ ] Bulk finalization (multiple clients)
- [ ] Photo upload (before/after)
- [ ] Tips/gratuity tracking
- [ ] Loyalty points on finalization

---

**This is a FUTURE feature. Implement after MVP is stable and running.**
