{% raw %}
# TASK-101: Create Master Model

**Status:** 📝 Design Complete
**Priority:** High
**Domain:** Team & Masters
**Estimate:** 3-4 hours

---

## Description

Create the `Master` model to represent salon specialists (stylists, nail technicians, cosmetologists, etc.). Each master has a profile page with biography, photo, specializations, certificates, and portfolio. Masters are linked to services and appointments.

## Acceptance Criteria

- [ ] `Master` model created in `features/booking/models/master.py`
- [ ] Translatable fields for bio and description (DE, RU, UK, EN)
- [ ] Photo field with upload path
- [ ] Specialization field (Many-to-Many with Service or Category)
- [ ] Slug field for URL (`/team/maria-ivanova/`)
- [ ] Active/Inactive status
- [ ] Display order for Team page
- [ ] Admin interface with inline editing
- [ ] Database migration created and tested

## Technical Details

### Model Structure

```python
from django.db import models
from django.utils.translation import gettext_lazy as _
from features.system.models.mixins import TimestampMixin, ActiveMixin, SeoMixin
from features.main.models import Category

class Master(TimestampMixin, ActiveMixin, SeoMixin):
    """
    Salon specialist (stylist, nail tech, cosmetologist, etc.)
    """

    # === Basic Information ===
    name = models.CharField(
        max_length=255,
        verbose_name=_("Full Name"),
        help_text=_("Master's full name (e.g. 'Maria Ivanova')")
    )

    slug = models.SlugField(
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("URL part (e.g. 'maria-ivanova')")
    )

    photo = models.ImageField(
        upload_to="masters/",
        blank=True,
        null=True,
        verbose_name=_("Profile Photo"),
        help_text=_("Professional portrait (recommended: 800x1000px)")
    )

    # === Professional Info (Translatable) ===
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Professional Title"),
        help_text=_("e.g. 'Top Colorist', 'Lead Nail Artist'")
    )

    bio = models.TextField(
        blank=True,
        verbose_name=_("Biography"),
        help_text=_("Full biography and work philosophy (HTML allowed)")
    )

    short_description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("Short Description"),
        help_text=_("Brief intro for Team page (1-2 sentences)")
    )

    # === Specializations (What master can do) ===
    service_groups = models.ManyToManyField(
        'main.ServiceGroup',
        related_name="masters",
        blank=True,
        verbose_name=_("Service Groups"),
        help_text=_("Specific service groups this master can perform (e.g. 'Manicure', 'Hair Coloring')")
    )

    categories = models.ManyToManyField(
        Category,
        related_name="masters",
        blank=True,
        verbose_name=_("Categories"),
        help_text=_("High-level categories for filtering (auto-filled from service_groups)")
    )

    # === Experience ===
    years_experience = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Years of Experience"),
        help_text=_("Total years working in the beauty industry")
    )

    # === Contact (Optional) ===
    instagram = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Instagram Handle"),
        help_text=_("Username only (e.g. 'maria.beauty')")
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Direct Phone"),
        help_text=_("Optional direct contact number")
    )

    # === Employment Status (instead of is_active) ===
    STATUS_ACTIVE = 'active'
    STATUS_VACATION = 'vacation'
    STATUS_FIRED = 'fired'
    STATUS_TRAINING = 'training'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, _('Active (Working)')),
        (STATUS_VACATION, _('On Vacation')),
        (STATUS_FIRED, _('Fired/Left')),
        (STATUS_TRAINING, _('In Training')),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name=_("Employment Status"),
        help_text=_("Current work status (we never delete masters, only change status)")
    )

    # === Flags ===
    is_owner = models.BooleanField(
        default=False,
        verbose_name=_("Is Owner"),
        help_text=_("Display as salon owner with special styling")
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name=_("Featured Master"),
        help_text=_("Show on homepage or in featured section")
    )

    # === Display Order ===
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Display Order"),
        help_text=_("Lower numbers appear first")
    )

    class Meta:
        verbose_name = _("Master")
        verbose_name_plural = _("Masters")
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('master_detail', kwargs={'slug': self.slug})

    @property
    def instagram_url(self):
        """Full Instagram profile URL"""
        if self.instagram:
            return f"https://instagram.com/{self.instagram.lstrip('@')}"
        return None

    @property
    def is_available_for_booking(self):
        """Check if master can accept new bookings"""
        return self.status == self.STATUS_ACTIVE

    def get_available_services(self):
        """Get all services this master can perform"""
        from features.main.models import Service
        return Service.objects.filter(
            group__in=self.service_groups.all(),
            is_active=True
        ).distinct()

    def can_perform_service(self, service):
        """Check if master can perform specific service"""
        return self.service_groups.filter(
            pk=service.group_id
        ).exists()

    def active_portfolio_count(self):
        """Count of published portfolio images"""
        return self.portfolio_images.filter(is_active=True).count()
```

### Translation Configuration

```python
# features/booking/translation.py
from modeltranslation.translator import translator, TranslationOptions
from .models import Master

class MasterTranslationOptions(TranslationOptions):
    fields = ('title', 'bio', 'short_description')

translator.register(Master, MasterTranslationOptions)
```

### Admin Configuration

```python
# features/booking/admin.py
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import Master

@admin.register(Master)
class MasterAdmin(TranslationAdmin):
    list_display = ['name', 'title', 'is_owner', 'is_featured', 'is_active', 'order']
    list_filter = ['is_active', 'is_owner', 'is_featured', 'categories']
    search_fields = ['name', 'title', 'instagram']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['categories']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'photo', 'order')
        }),
        (_('Professional Info'), {
            'fields': ('title', 'short_description', 'bio', 'years_experience')
        }),
        (_('Specializations'), {
            'fields': ('categories',)
        }),
        (_('Contact'), {
            'fields': ('instagram', 'phone'),
            'classes': ('collapse',)
        }),
        (_('Flags'), {
            'fields': ('is_owner', 'is_featured', 'is_active')
        }),
        (_('SEO'), {
            'fields': ('seo_title', 'seo_description', 'seo_image'),
            'classes': ('collapse',)
        }),
    )
```

## Dependencies

- **Requires:** `features/main/models/category.py` (Category model)
- **Requires:** `features/system/models/mixins.py` (SeoMixin, TimestampMixin)
- **Requires:** `django-modeltranslation` package
- **Blocks:** TASK-102 (Master Portfolio)
- **Blocks:** TASK-103 (Master Certificates)
- **Blocks:** TASK-104 (Master Detail Page)

## Related Files

- **Create:** `src/backend_django/features/booking/models/master.py`
- **Update:** `src/backend_django/features/booking/models/__init__.py`
- **Create:** `src/backend_django/features/booking/translation.py`
- **Update:** `src/backend_django/features/booking/admin.py`
- **Create Migration:** `features/booking/migrations/000X_master.py`

## Testing Checklist

- [ ] Create master with all fields → success
- [ ] Create master without photo → success (optional field)
- [ ] Slug auto-populates in admin from name
- [ ] `is_owner=True` master displays differently in templates
- [ ] Translation works for bio and title (all 4 languages)
- [ ] Categories filter works in admin
- [ ] `get_absolute_url()` returns correct URL
- [ ] `instagram_url` property handles `@` prefix correctly
- [ ] Ordering by `order` field works on Team page

## Template Integration

### Team Page (`templates/team/team.html`)

```django
<!-- Owner Block (is_owner=True) -->
{% for master in owner %}
<section class="owner-block">
    <img src="{{ master.photo.url }}" alt="{{ master.name }}">
    <h2>{{ master.name }}</h2>
    <p>{{ master.bio }}</p>
    <a href="{{ master.get_absolute_url }}" class="btn-pill">{% trans "View Profile" %}</a>
</section>
{% endfor %}

<!-- Masters Grid -->
<div class="masters-grid">
    {% for master in masters %}
    <div class="master-card">
        <img src="{{ master.photo.url }}" alt="{{ master.name }}">
        <h3>{{ master.name }}</h3>
        <p class="master-title">{{ master.title }}</p>
        <a href="{{ master.get_absolute_url }}">{% trans "View Profile" %}</a>
    </div>
    {% endfor %}
</div>
```

## Future Enhancements

- Add `availability_status` (available, busy, on_vacation)
- Add `rating` field (average from reviews)
- Add `booking_preferences` JSON field (preferred days, break times)
- Implement master calendar view in admin
- Add master statistics dashboard (bookings, revenue)
{% endraw %}
