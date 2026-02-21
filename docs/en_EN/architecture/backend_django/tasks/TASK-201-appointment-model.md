# TASK-201: Create Appointment Model

**Status:** 📝 Design Complete
**Priority:** Critical
**Domain:** Booking System
**Estimate:** 5-7 hours

---

## Description

Create the `Appointment` model to store client bookings. This is the core model for the booking system, linking clients, masters, and services with date/time slots. Supports status tracking, cancellation, and rescheduling.

## Acceptance Criteria

- [ ] `Appointment` model created in `features/booking/models/appointment.py`
- [ ] Foreign keys to Client, Master, Service
- [ ] DateTime field for appointment start
- [ ] Duration field (calculated from service or manual)
- [ ] Status field (pending, confirmed, completed, cancelled)
- [ ] Cancellation reason and timestamp tracking
- [ ] Price snapshot (in case service price changes)
- [ ] Admin interface with filters and actions
- [ ] Database migration created and tested
- [ ] Validation prevents double-booking

## Technical Details

### Model Structure

```python
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from features.system.models.mixins import TimestampMixin
from .client import Client
from .master import Master
from features.main.models import Service

class Appointment(TimestampMixin):
    """
    Client booking/appointment with a master for a specific service.
    """

    # === Core Relationships ===
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name=_("Client")
    )

    master = models.ForeignKey(
        Master,
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name=_("Master")
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name=_("Service")
    )

    # === Scheduling ===
    datetime_start = models.DateTimeField(
        verbose_name=_("Start Date & Time"),
        db_index=True,
        help_text=_("Appointment start time")
    )

    duration_minutes = models.PositiveIntegerField(
        verbose_name=_("Duration (minutes)"),
        help_text=_("Service duration (auto-filled from Service model)")
    )

    # === Pricing (Snapshot) ===
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Price (€)"),
        help_text=_("Price at booking time (snapshot)")
    )

    # === Status Tracking ===
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_NO_SHOW = 'no_show'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending Confirmation')),
        (STATUS_CONFIRMED, _('Confirmed')),
        (STATUS_COMPLETED, _('Completed')),
        (STATUS_CANCELLED, _('Cancelled')),
        (STATUS_NO_SHOW, _('No Show')),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name=_("Status")
    )

    # === Cancellation Info ===
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Cancelled At")
    )

    CANCEL_REASON_CLIENT = 'client'
    CANCEL_REASON_MASTER = 'master'
    CANCEL_REASON_RESCHEDULE = 'reschedule'
    CANCEL_REASON_OTHER = 'other'

    CANCEL_REASON_CHOICES = [
        (CANCEL_REASON_CLIENT, _('Cancelled by Client')),
        (CANCEL_REASON_MASTER, _('Cancelled by Master')),
        (CANCEL_REASON_RESCHEDULE, _('Rescheduled')),
        (CANCEL_REASON_OTHER, _('Other')),
    ]

    cancel_reason = models.CharField(
        max_length=20,
        choices=CANCEL_REASON_CHOICES,
        blank=True,
        verbose_name=_("Cancellation Reason")
    )

    cancel_note = models.TextField(
        blank=True,
        verbose_name=_("Cancellation Note"),
        help_text=_("Additional details about cancellation")
    )

    # === Client Notes ===
    client_notes = models.TextField(
        blank=True,
        verbose_name=_("Client Notes"),
        help_text=_("Special requests from client (e.g. allergies, preferences)")
    )

    # === Admin Notes ===
    admin_notes = models.TextField(
        blank=True,
        verbose_name=_("Admin Notes"),
        help_text=_("Internal notes (not visible to client)")
    )

    # === Notifications ===
    reminder_sent = models.BooleanField(
        default=False,
        verbose_name=_("Reminder Sent"),
        help_text=_("SMS/Email reminder was sent")
    )

    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Reminder Sent At")
    )

    class Meta:
        verbose_name = _("Appointment")
        verbose_name_plural = _("Appointments")
        ordering = ['-datetime_start']
        indexes = [
            models.Index(fields=['master', 'datetime_start']),
            models.Index(fields=['client', 'datetime_start']),
            models.Index(fields=['status', 'datetime_start']),
        ]

    def __str__(self):
        return f"{self.client.display_name()} → {self.master.name} ({self.datetime_start.strftime('%Y-%m-%d %H:%M')})"

    def save(self, *args, **kwargs):
        """Auto-fill duration and price from service"""
        if not self.duration_minutes:
            self.duration_minutes = self.service.duration
        if not self.price:
            self.price = self.service.price
        super().save(*args, **kwargs)

    def clean(self):
        """Validate no double-booking"""
        if not self.pk:  # Only for new appointments
            conflicts = Appointment.objects.filter(
                master=self.master,
                datetime_start__lt=self.datetime_end,
                datetime_end__gt=self.datetime_start,
                status__in=[self.STATUS_PENDING, self.STATUS_CONFIRMED]
            ).exists()

            if conflicts:
                raise ValidationError({
                    'datetime_start': _('This time slot is already booked.')
                })

    @property
    def datetime_end(self):
        """Calculate appointment end time"""
        from datetime.timedelta import timedelta
        return self.datetime_start + timedelta(minutes=self.duration_minutes)

    @property
    def is_past(self):
        """Check if appointment is in the past"""
        return self.datetime_start < timezone.now()

    @property
    def is_upcoming(self):
        """Check if appointment is in the future"""
        return self.datetime_start > timezone.now()

    @property
    def is_today(self):
        """Check if appointment is today"""
        today = timezone.now().date()
        return self.datetime_start.date() == today

    def can_cancel(self):
        """Check if appointment can be cancelled"""
        if self.status in [self.STATUS_CANCELLED, self.STATUS_COMPLETED]:
            return False
        # Add time restriction (e.g. can't cancel within 2 hours)
        hours_until = (self.datetime_start - timezone.now()).total_seconds() / 3600
        return hours_until >= 2

    def cancel(self, reason=CANCEL_REASON_CLIENT, note=''):
        """Cancel appointment"""
        if not self.can_cancel():
            raise ValidationError(_('This appointment cannot be cancelled.'))

        self.status = self.STATUS_CANCELLED
        self.cancelled_at = timezone.now()
        self.cancel_reason = reason
        self.cancel_note = note
        self.save(update_fields=['status', 'cancelled_at', 'cancel_reason', 'cancel_note', 'updated_at'])

    def mark_completed(self):
        """Mark appointment as completed"""
        if self.status != self.STATUS_CONFIRMED:
            raise ValidationError(_('Only confirmed appointments can be marked as completed.'))

        self.status = self.STATUS_COMPLETED
        self.save(update_fields=['status', 'updated_at'])

    def send_reminder(self):
        """Send reminder notification (to be implemented)"""
        # TODO: Implement SMS/Email sending
        self.reminder_sent = True
        self.reminder_sent_at = timezone.now()
        self.save(update_fields=['reminder_sent', 'reminder_sent_at'])
```

### Admin Configuration

```python
# features/booking/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'client_name', 'master', 'service',
        'datetime_start', 'duration_minutes', 'status_badge', 'price'
    ]
    list_filter = ['status', 'master', 'datetime_start', 'created_at']
    search_fields = [
        'client__name', 'client__phone', 'client__email',
        'master__name', 'service__title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'cancelled_at', 'reminder_sent_at']
    date_hierarchy = 'datetime_start'

    fieldsets = (
        (_('Booking Details'), {
            'fields': ('client', 'master', 'service', 'datetime_start', 'duration_minutes', 'price')
        }),
        (_('Status'), {
            'fields': ('status', 'cancelled_at', 'cancel_reason', 'cancel_note')
        }),
        (_('Notes'), {
            'fields': ('client_notes', 'admin_notes')
        }),
        (_('Notifications'), {
            'fields': ('reminder_sent', 'reminder_sent_at'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_confirmed', 'mark_as_completed', 'cancel_appointments']

    def client_name(self, obj):
        return obj.client.display_name()
    client_name.short_description = _('Client')

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'confirmed': 'green',
            'completed': 'blue',
            'cancelled': 'red',
            'no_show': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="padding:3px 10px;background:{};color:white;border-radius:3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = _('Status')

    def mark_as_confirmed(self, request, queryset):
        queryset.update(status=Appointment.STATUS_CONFIRMED)
    mark_as_confirmed.short_description = _('Mark as Confirmed')

    def mark_as_completed(self, request, queryset):
        queryset.update(status=Appointment.STATUS_COMPLETED)
    mark_as_completed.short_description = _('Mark as Completed')

    def cancel_appointments(self, request, queryset):
        queryset.update(
            status=Appointment.STATUS_CANCELLED,
            cancel_reason=Appointment.CANCEL_REASON_OTHER
        )
    cancel_appointments.short_description = _('Cancel Selected')
```

## Dependencies

- **Requires:** TASK-301 (Client model)
- **Requires:** TASK-101 (Master model)
- **Requires:** `features/main/models/service.py` (Service model)
- **Blocks:** TASK-204 (Booking Form UI)
- **Blocks:** TASK-206 (Notifications)

## Related Files

- **Create:** `src/backend_django/features/booking/models/appointment.py`
- **Update:** `src/backend_django/features/booking/models/__init__.py`
- **Update:** `src/backend_django/features/booking/admin.py`
- **Create Migration:** `features/booking/migrations/000X_appointment.py`

## Testing Checklist

- [ ] Create appointment with all required fields → success
- [ ] Duration auto-fills from service
- [ ] Price snapshot saves correctly
- [ ] Double-booking validation prevents conflicts
- [ ] `datetime_end` property calculates correctly
- [ ] `can_cancel()` respects 2-hour policy
- [ ] `cancel()` method updates status and timestamp
- [ ] Admin actions work (confirm, complete, cancel)
- [ ] Search works by client name, phone, master
- [ ] Status badge colors display correctly

## Future Enhancements

- Add payment integration (paid, pending, refund)
- Add recurring appointments (weekly manicure)
- Add appointment packages (5 sessions for price of 4)
- Implement "Time Tetris" auto-optimization
- Add waitlist functionality
- Add online payment status tracking
