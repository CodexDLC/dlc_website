# TASK-301: Create Client Model (Ghost User System)

**Status:** 📝 Design Complete
**Priority:** Critical
**Domain:** Client Management
**Estimate:** 4-6 hours

---

## Description

Create the `Client` model as the central entity for customer management. This model supports the **Ghost User** pattern where clients are automatically created during booking without explicit registration. The model can optionally link to a Django `User` when the client activates their account.

## Acceptance Criteria

- [ ] `Client` model created in `features/booking/models/client.py`
- [ ] Model supports creation without Django User (ghost mode)
- [ ] Phone and email fields with proper indexing
- [ ] Unique access token generation for password-less management
- [ ] Status field for tracking activation state
- [ ] OneToOne relationship to Django User (nullable)
- [ ] Admin interface configured with search and filters
- [ ] Database migration created and tested
- [ ] Model methods documented with docstrings

## Technical Details

### Model Structure

```python
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from features.system.models.mixins import TimestampMixin
import uuid

User = get_user_model()

class Client(TimestampMixin):
    """
    Client profile (salon customer).
    Can exist WITHOUT Django User (ghost) or be linked after activation.
    """

    # === Contact Information ===
    phone = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        verbose_name=_("Phone Number"),
        help_text=_("Primary contact method")
    )
    email = models.EmailField(
        blank=True,
        db_index=True,
        verbose_name=_("Email"),
        help_text=_("Email for notifications and account activation")
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Full Name"),
        help_text=_("Client's name (collected during booking)")
    )

    # === Django User Link (Optional) ===
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_profile',
        verbose_name=_("Django User Account"),
        help_text=_("Linked when client activates account")
    )

    # === Access Control ===
    access_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name=_("Access Token"),
        help_text=_("Used in SMS/Email links for appointment management")
    )

    # === Status Tracking ===
    STATUS_GUEST = 'guest'
    STATUS_ACTIVE = 'active'
    STATUS_BLOCKED = 'blocked'

    STATUS_CHOICES = [
        (STATUS_GUEST, _('Guest (Temporary)')),
        (STATUS_ACTIVE, _('Active (Registered)')),
        (STATUS_BLOCKED, _('Blocked')),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_GUEST,
        db_index=True,
        verbose_name=_("Status")
    )

    # === Marketing ===
    consent_marketing = models.BooleanField(
        default=False,
        verbose_name=_("Marketing Consent"),
        help_text=_("Client agreed to receive promotional materials")
    )
    consent_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Consent Given Date")
    )

    # === Admin Notes ===
    notes = models.TextField(
        blank=True,
        verbose_name=_("Internal Notes"),
        help_text=_("Admin-only notes about the client")
    )

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'status']),
            models.Index(fields=['email', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(phone='', email=''),
                name='client_must_have_contact'
            )
        ]

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.phone or self.email})"
        return self.phone or self.email or f"Client #{self.pk}"

    def save(self, *args, **kwargs):
        """Generate access token on creation"""
        if not self.access_token:
            self.access_token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def display_name(self):
        """Name for public display (hides contact info if no name)"""
        return self.name if self.name else _("Guest")

    def activate_account(self, user):
        """Link to Django User and activate account"""
        self.user = user
        self.status = self.STATUS_ACTIVE
        self.save(update_fields=['user', 'status', 'updated_at'])

    @property
    def is_ghost(self):
        """Check if this is a temporary ghost account"""
        return self.status == self.STATUS_GUEST and self.user is None

    @property
    def primary_contact(self):
        """Return primary contact method"""
        return self.phone or self.email
```

### Admin Configuration

```python
# features/booking/admin.py
from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'phone', 'email', 'status', 'is_ghost', 'created_at']
    list_filter = ['status', 'consent_marketing', 'created_at']
    search_fields = ['name', 'phone', 'email', 'access_token']
    readonly_fields = ['access_token', 'created_at', 'updated_at']

    fieldsets = (
        (_('Contact Information'), {
            'fields': ('name', 'phone', 'email')
        }),
        (_('Account Status'), {
            'fields': ('status', 'user', 'access_token')
        }),
        (_('Marketing'), {
            'fields': ('consent_marketing', 'consent_date')
        }),
        (_('Internal'), {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def is_ghost(self, obj):
        return obj.is_ghost
    is_ghost.boolean = True
    is_ghost.short_description = _('Ghost Account')
```

## Dependencies

- **Requires:** `TimestampMixin` from `features/system/models/mixins.py`
- **Blocks:** TASK-302 (Ghost User Service)
- **Blocks:** TASK-201 (Appointment Model - needs FK to Client)

## Related Files

- **Create:** `src/backend_django/features/booking/models/client.py`
- **Create:** `src/backend_django/features/booking/models/__init__.py`
- **Update:** `src/backend_django/features/booking/admin.py`
- **Create Migration:** `features/booking/migrations/0001_initial.py`

## Testing Checklist

- [ ] Create ghost client without phone/email → should fail (constraint)
- [ ] Create ghost client with phone only → success
- [ ] Create ghost client with email only → success
- [ ] Access token is auto-generated on save
- [ ] `display_name()` returns "Guest" for unnamed clients
- [ ] `activate_account()` links User and changes status
- [ ] Admin search works for phone, email, name
- [ ] Admin filter works for status and marketing consent

## GDPR Compliance Notes

- Client data is stored with legitimate interest (booking)
- `notes` field is admin-only (not exposed to client)
- Access token allows data management without authentication
- Must implement data export/deletion endpoints (future task)
- Marketing consent must be explicit (checkbox with timestamp)

## Future Enhancements

- Add `telegram_id` field for bot integration (TASK-504)
- Add `preferred_language` field for i18n
- Add `last_visit` field for retention logic
- Implement automatic data anonymization after X months of inactivity
