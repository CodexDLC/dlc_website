# TASK-MVP-001: Simple Booking Form with Admin Approval

**Status:** 🎯 MVP - Critical for Launch
**Priority:** Critical
**Domain:** Booking System (MVP)
**Estimate:** 6-8 hours

---

## Description

Implement a simple booking form for the website that sends booking requests to the salon owner for manual approval. This is the **MVP version** before implementing the full booking system with masters, schedules, and QR finalization.

**Key principle:** Keep it simple for launch. Advanced features (master selection, automatic scheduling, QR codes) will be added later.

## Acceptance Criteria

- [ ] `BookingRequest` model created (without Master/Client dependencies)
- [ ] Booking form on website (HTMX or simple POST)
- [ ] Email notification to owner on new request
- [ ] Telegram Bot notification to owner with approve/reject buttons
- [ ] Owner can approve → client receives confirmation email/telegram
- [ ] Owner can reject → client receives rejection with reason
- [ ] Admin interface for viewing all booking requests
- [ ] Client receives auto-reply "We'll contact you soon"

## Technical Details

### 1. Model (Minimal MVP)

```python
# features/booking/models/booking_request.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from features.system.models.mixins import TimestampMixin
from features.main.models import Service

class BookingRequest(TimestampMixin):
    """
    Booking request (before owner approval).
    Simple model for MVP - no Master/Client relations yet.
    """

    # Client info
    client_name = models.CharField(max_length=255, verbose_name=_("Name"))
    client_phone = models.CharField(max_length=20, verbose_name=_("Phone"))
    client_email = models.EmailField(blank=True, verbose_name=_("Email"))
    client_telegram_id = models.BigIntegerField(null=True, blank=True)

    # Booking details
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    preferred_date = models.DateField(verbose_name=_("Preferred Date"))
    preferred_time = models.TimeField(verbose_name=_("Preferred Time"))
    client_comment = models.TextField(blank=True, verbose_name=_("Comment"))

    # Status
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_REJECTED, _('Rejected')),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )

    processed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    admin_notes = models.TextField(blank=True)

    # Future migration support
    converted_to_client_id = models.IntegerField(null=True, blank=True)
    converted_to_appointment_id = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = _("Booking Request")
        verbose_name_plural = _("Booking Requests")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client_name} - {self.service.title}"

    def approve(self):
        self.status = self.STATUS_APPROVED
        self.processed_at = timezone.now()
        self.save()

    def reject(self, reason=''):
        self.status = self.STATUS_REJECTED
        self.processed_at = timezone.now()
        self.rejection_reason = reason
        self.save()
```

### 2. Booking Form View

```python
# features/booking/views/booking_form.py
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.translation import gettext as _
from features.booking.models import BookingRequest
from features.booking.services.notifications import send_booking_notifications

@require_http_methods(["GET", "POST"])
def booking_form_view(request, service_slug=None):
    """
    Booking form page.
    URL: /booking/ or /services/{slug}/book/
    """
    from features.main.models import Service, Category

    services = Service.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(is_active=True).prefetch_related('services')

    # Pre-select service if coming from service page
    selected_service = None
    if service_slug:
        selected_service = Service.objects.filter(slug=service_slug).first()

    if request.method == 'POST':
        # Extract form data
        booking_request = BookingRequest.objects.create(
            client_name=request.POST['name'],
            client_phone=request.POST['phone'],
            client_email=request.POST.get('email', ''),
            service_id=request.POST['service_id'],
            preferred_date=request.POST['date'],
            preferred_time=request.POST['time'],
            client_comment=request.POST.get('comment', '')
        )

        # Send notifications
        send_booking_notifications(booking_request)

        # Show success message
        messages.success(request, _(
            "Your booking request has been sent! "
            "We will contact you within 24 hours to confirm."
        ))

        return redirect('booking_success')

    context = {
        'services': services,
        'categories': categories,
        'selected_service': selected_service,
    }

    return render(request, 'booking/booking_form.html', context)
```

### 3. Notification Service

```python
# features/booking/services/notifications.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import httpx

def send_booking_notifications(booking_request):
    """
    Send notifications to owner via Email and Telegram.
    """
    # 1. Send email to owner
    send_email_to_owner(booking_request)

    # 2. Send telegram notification to owner
    send_telegram_to_owner(booking_request)

    # 3. Send auto-reply to client
    send_client_auto_reply(booking_request)


def send_email_to_owner(booking_request):
    """Email to salon owner"""
    subject = f"🔔 Neue Buchungsanfrage - {booking_request.client_name}"

    html_content = render_to_string('emails/new_booking_request_owner.html', {
        'request': booking_request
    })

    send_mail(
        subject=subject,
        message='',  # Plain text fallback
        html_message=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.OWNER_EMAIL],
        fail_silently=False,
    )


def send_telegram_to_owner(booking_request):
    """Telegram notification with approve/reject buttons"""
    import httpx

    bot_token = settings.TELEGRAM_BOT_TOKEN
    owner_chat_id = settings.OWNER_TELEGRAM_CHAT_ID

    text = (
        f"🔔 <b>Neue Buchungsanfrage!</b>\n\n"
        f"👤 Name: <b>{booking_request.client_name}</b>\n"
        f"📞 Telefon: {booking_request.client_phone}\n"
        f"📧 Email: {booking_request.client_email or 'Keine'}\n\n"
        f"💅 Service: <b>{booking_request.service.title}</b>\n"
        f"📅 Datum: {booking_request.preferred_date.strftime('%d.%m.%Y')}\n"
        f"⏰ Uhrzeit: {booking_request.preferred_time.strftime('%H:%M')}\n\n"
        f"💬 Kommentar: {booking_request.client_comment or 'Keine'}"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Bestätigen", "callback_data": f"approve_booking:{booking_request.id}"},
                {"text": "❌ Ablehnen", "callback_data": f"reject_booking:{booking_request.id}"}
            ],
            [
                {"text": "📝 In Admin öffnen", "url": f"{settings.SITE_URL}/admin/booking/bookingrequest/{booking_request.id}/change/"}
            ]
        ]
    }

    httpx.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": owner_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        }
    )


def send_client_auto_reply(booking_request):
    """Auto-reply to client"""
    if booking_request.client_email:
        subject = "Ihre Buchungsanfrage bei LILY Beauty Salon"

        html_content = render_to_string('emails/booking_auto_reply_client.html', {
            'request': booking_request
        })

        send_mail(
            subject=subject,
            message='',
            html_message=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking_request.client_email],
            fail_silently=True,
        )


def send_approval_to_client(booking_request):
    """Notify client: booking approved"""
    # Email
    if booking_request.client_email:
        subject = "✅ Ihr Termin ist bestätigt - LILY Salon"
        html = render_to_string('emails/booking_approved.html', {'request': booking_request})
        send_mail(subject, '', settings.DEFAULT_FROM_EMAIL, [booking_request.client_email], html_message=html)

    # Telegram (if available)
    if booking_request.client_telegram_id:
        # TODO: send via 02_telegram_bot


def send_rejection_to_client(booking_request):
    """Notify client: booking rejected"""
    # Email
    if booking_request.client_email:
        subject = "Ihre Buchungsanfrage - LILY Salon"
        html = render_to_string('emails/booking_rejected.html', {
            'request': booking_request,
            'reason': booking_request.rejection_reason
        })
        send_mail(subject, '', settings.DEFAULT_FROM_EMAIL, [booking_request.client_email], html_message=html)

    # Telegram (if available)
    if booking_request.client_telegram_id:
        # TODO: send via 02_telegram_bot
```

### 4. Telegram Bot Handler (Owner Actions)

```python
# src/telegram_bot/features/owner_panel/handlers.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
import httpx

router = Router()

@router.callback_query(F.data.startswith("approve_booking:"))
async def approve_booking(callback: CallbackQuery):
    """Owner approves booking request"""
    booking_id = callback.data.split(":")[1]

    # Call Django API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DJANGO_API_URL}/api/02_telegram_bot/booking/approve/",
            json={"booking_id": booking_id}
        )

    if response.status_code == 200:
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>Bestätigt!</b>",
            parse_mode="HTML"
        )
        await callback.answer("✅ Buchung bestätigt. Kunde wurde benachrichtigt.")
    else:
        await callback.answer("❌ Fehler", show_alert=True)


@router.callback_query(F.data.startswith("reject_booking:"))
async def reject_booking_prompt(callback: CallbackQuery):
    """Owner rejects - show reason options"""
    booking_id = callback.data.split(":")[1]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Keine freie Zeit",
            callback_data=f"reject_reason:{booking_id}:no_slots"
        )],
        [InlineKeyboardButton(
            text="Service nicht verfügbar",
            callback_data=f"reject_reason:{booking_id}:service_unavailable"
        )],
        [InlineKeyboardButton(
            text="Andere Grund...",
            callback_data=f"reject_reason:{booking_id}:other"
        )],
        [InlineKeyboardButton(
            text="« Zurück",
            callback_data=f"back_to_booking:{booking_id}"
        )]
    ])

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("reject_reason:"))
async def reject_with_reason(callback: CallbackQuery):
    """Apply rejection with reason"""
    _, booking_id, reason_code = callback.data.split(":")

    reason_texts = {
        "no_slots": "Leider haben wir zu diesem Zeitpunkt keine freien Termine.",
        "service_unavailable": "Dieser Service ist derzeit nicht verfügbar.",
        "other": "Wir können Ihre Anfrage leider nicht bestätigen."
    }

    reason = reason_texts.get(reason_code, reason_texts['other'])

    # Call Django API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DJANGO_API_URL}/api/02_telegram_bot/booking/reject/",
            json={
                "booking_id": booking_id,
                "reason": reason
            }
        )

    if response.status_code == 200:
        await callback.message.edit_text(
            callback.message.text + f"\n\n❌ <b>Abgelehnt</b>\nGrund: {reason}",
            parse_mode="HTML"
        )
        await callback.answer("❌ Buchung abgelehnt. Kunde wurde benachrichtigt.")
```

### 5. Django Admin

```python
# features/booking/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import BookingRequest

@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'created_at', 'client_name', 'client_phone',
        'service', 'preferred_datetime', 'status_badge'
    ]
    list_filter = ['status', 'created_at', 'service__category']
    search_fields = ['client_name', 'client_phone', 'client_email']
    readonly_fields = ['created_at', 'updated_at', 'processed_at']

    actions = ['approve_requests', 'reject_requests']

    fieldsets = (
        ('Client Info', {
            'fields': ('client_name', 'client_phone', 'client_email')
        }),
        ('Booking Details', {
            'fields': ('service', 'preferred_date', 'preferred_time', 'client_comment')
        }),
        ('Status', {
            'fields': ('status', 'processed_at', 'rejection_reason', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def preferred_datetime(self, obj):
        return f"{obj.preferred_date} {obj.preferred_time}"
    preferred_datetime.short_description = 'Date & Time'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
        }
        return format_html(
            '<span style="padding:3px 10px;background:{};color:white;border-radius:3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def approve_requests(self, request, queryset):
        for booking in queryset:
            booking.approve()
            send_approval_to_client(booking)
    approve_requests.short_description = 'Approve selected'

    def reject_requests(self, request, queryset):
        for booking in queryset:
            booking.reject(reason='Bulk rejection from admin')
            send_rejection_to_client(booking)
    reject_requests.short_description = 'Reject selected'
```

## Dependencies

- **Requires:** `features/main/models/service.py` (Service model exists)
- **Requires:** Email configuration in settings
- **Requires:** Telegram Bot token and owner chat ID
- **Blocks:** Future full booking system (this is stepping stone)

## Migration Path to Full System

When implementing full booking system (TASK-201, TASK-301):

```python
# Migration script
def convert_booking_requests_to_appointments():
    """Convert approved BookingRequests to Client + Appointment"""
    for request in BookingRequest.objects.filter(
        status=BookingRequest.STATUS_APPROVED,
        converted_to_client_id__isnull=True
    ):
        # Create Client (Ghost User)
        client = Client.objects.create(
            name=request.client_name,
            phone=request.client_phone,
            email=request.client_email,
            status=Client.STATUS_GUEST
        )

        # Create Appointment (if Master system ready)
        # appointment = Appointment.objects.create(...)

        # Link back
        request.converted_to_client_id = client.id
        request.save()
```

## Settings Required

```python
# settings/base_module.py or .env

# Email
DEFAULT_FROM_EMAIL = 'noreply@lily-salon.de'
OWNER_EMAIL = 'owner@lily-salon.de'

# Telegram
TELEGRAM_BOT_TOKEN = 'your_bot_token'
OWNER_TELEGRAM_CHAT_ID = 123456789  # Owner's Telegram chat ID

# Site
SITE_URL = 'https://lily-salon.de'
```

## Testing Checklist

- [ ] Fill booking form → BookingRequest created
- [ ] Owner receives email with booking details
- [ ] Owner receives Telegram message with buttons
- [ ] Click "Approve" → client receives confirmation email
- [ ] Click "Reject" → owner selects reason → client receives rejection
- [ ] Admin can view all requests
- [ ] Admin can bulk approve/reject
- [ ] Form validation works (required fields)
- [ ] HTMX interactions (if used) work smoothly

## Email Templates

Create these templates:
- `templates/emails/new_booking_request_owner.html`
- `templates/emails/booking_auto_reply_client.html`
- `templates/emails/booking_approved.html`
- `templates/emails/booking_rejected.html`

## Future Enhancements (Not MVP)

- [ ] SMS notifications (Twilio integration)
- [ ] Calendar integration (Google Calendar)
- [ ] Automatic conflict detection
- [ ] Master selection
- [ ] QR code finalization
- [ ] Payment integration

---

**This is the MINIMUM VIABLE PRODUCT for launch. Get it working, then iterate!**
