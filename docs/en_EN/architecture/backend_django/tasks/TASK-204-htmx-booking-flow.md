{% raw %}
# TASK-204: HTMX Booking Flow (SEO-Friendly Dynamic Booking)

**Status:** 📝 Design Complete
**Priority:** Critical
**Domain:** Booking System
**Estimate:** 8-12 hours

---

## Description

Implement dynamic booking flow using **HTMX** for real-time interactions without losing SEO benefits. Support two booking paths:
1. **Service → Master → Time** (user selects service first)
2. **Master → Service → Time** (user selects master first)

All interactions use server-side rendering with HTMX for progressive enhancement.

## Acceptance Criteria

- [ ] HTMX integrated in base template
- [ ] Service selection updates master list dynamically
- [ ] Master selection updates available time slots
- [ ] Both booking paths work (service-first, master-first)
- [ ] SEO-friendly URLs (`/book/`, `/book/service/manicure/`, `/team/maria/`)
- [ ] Loading states and error handling
- [ ] Mobile-responsive design
- [ ] Accessibility (keyboard navigation, ARIA labels)

## Technical Details

### HTMX Setup

```html
<!-- templates/base_module.html -->
<head>
    ...
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <meta name="htmx-config" content='{"timeout":5000}'>
</head>
```

### Booking Flow Architecture

```
┌─────────────────────────────────────────────────────┐
│  PATH A: Service-First Booking                      │
│                                                      │
│  /services/manicure/  (SEO page)                    │
│       ↓                                              │
│  [Select Service] → HTMX → /api/masters/?service_id │
│       ↓                                              │
│  [Select Master] → HTMX → /api/slots/?master&service│
│       ↓                                              │
│  [Select Time] → Form Submit → /booking/confirm/    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  PATH B: Master-First Booking                       │
│                                                      │
│  /team/maria/  (SEO page)                           │
│       ↓                                              │
│  [Select Master] → HTMX → /api/services/?master_id  │
│       ↓                                              │
│  [Select Service] → HTMX → /api/slots/?master&service│
│       ↓                                              │
│  [Select Time] → Form Submit → /booking/confirm/    │
└─────────────────────────────────────────────────────┘
```

### Views Structure

```python
# features/booking/views/booking_flow.py
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from features.main.models import Service, ServiceGroup
from features.booking.models import Master
from features.booking.services.slot_finder import find_available_slots

# === PATH A: Service Page (SEO) ===
@require_GET
def service_booking_page(request, service_slug):
    """
    Full SEO page with booking widget.
    URL: /services/manicure/book/
    """
    service = get_object_or_404(Service, slug=service_slug, is_active=True)

    context = {
        'service': service,
        'seo': service.get_seo(),
        'initial_masters': service.group.masters.filter(status=Master.STATUS_ACTIVE)
    }

    return render(request, 'booking/service_booking.html', context)


# === PATH B: Master Page (SEO) ===
@require_GET
def master_booking_page(request, master_slug):
    """
    Full SEO page with booking widget.
    URL: /team/maria/book/
    """
    master = get_object_or_404(Master, slug=master_slug, status=Master.STATUS_ACTIVE)

    context = {
        'master': master,
        'seo': master.get_seo(),
        'available_services': master.get_available_services()
    }

    return render(request, 'booking/master_booking.html', context)


# === HTMX Partials (API-like endpoints) ===
@require_GET
def htmx_masters_for_service(request):
    """
    HTMX endpoint: Return master list for selected service.
    GET /booking/htmx/masters/?service_id=123
    """
    service_id = request.GET.get('service_id')
    service = get_object_or_404(Service, pk=service_id)

    # Find masters who can perform this service
    masters = Master.objects.filter(
        service_groups=service.group,
        status=Master.STATUS_ACTIVE
    ).distinct()

    return render(request, 'booking/partials/_master_list.html', {
        'masters': masters,
        'service': service
    })


@require_GET
def htmx_services_for_master(request):
    """
    HTMX endpoint: Return service list for selected master.
    GET /booking/htmx/services/?master_id=5
    """
    master_id = request.GET.get('master_id')
    master = get_object_or_404(Master, pk=master_id, status=Master.STATUS_ACTIVE)

    services = master.get_available_services()

    return render(request, 'booking/partials/_service_list.html', {
        'services': services,
        'master': master
    })


@require_GET
def htmx_time_slots(request):
    """
    HTMX endpoint: Return available time slots.
    GET /booking/htmx/slots/?master_id=5&service_id=123&date=2024-03-15
    """
    master_id = request.GET.get('master_id')
    service_id = request.GET.get('service_id')
    date_str = request.GET.get('date')  # ISO format

    master = get_object_or_404(Master, pk=master_id)
    service = get_object_or_404(Service, pk=service_id)

    # Validate master can perform service
    if not master.can_perform_service(service):
        return render(request, 'booking/partials/_error.html', {
            'error': 'This master cannot perform this service.'
        }, status=400)

    # Find available slots
    slots = find_available_slots(
        master=master,
        service=service,
        date=date_str
    )

    return render(request, 'booking/partials/_time_slots.html', {
        'slots': slots,
        'master': master,
        'service': service,
        'date': date_str
    })


@require_POST
def booking_confirm(request):
    """
    Final step: Create appointment and redirect to confirmation.
    POST /booking/confirm/
    """
    # Extract form data
    master_id = request.POST.get('master_id')
    service_id = request.POST.get('service_id')
    datetime_start = request.POST.get('datetime_start')
    client_name = request.POST.get('name')
    client_phone = request.POST.get('phone')
    client_email = request.POST.get('email', '')

    # Create or find ghost client
    from features.booking.services.ghost_user import create_or_update_ghost_client
    client = create_or_update_ghost_client(
        phone=client_phone,
        email=client_email,
        name=client_name
    )

    # Create appointment
    from features.booking.models import Appointment
    appointment = Appointment.objects.create(
        client=client,
        master_id=master_id,
        service_id=service_id,
        datetime_start=datetime_start,
        status=Appointment.STATUS_PENDING
    )

    # Send confirmation SMS/Email
    # TODO: TASK-206 notifications

    return redirect('booking_success', token=client.access_token)
```

### Templates Structure

#### Main Booking Page (Service-First)

```django
{# templates/booking/service_booking.html #}
{% extends "base.html" %}
{% load static i18n %}

{% block content %}
<section class="booking-page">
    <div class="container">
        <h1>{% trans "Book" %} {{ service.title }}</h1>

        <div id="booking-widget">
            {# Step 1: Service (pre-selected) #}
            <div class="booking-step active">
                <h3>{% trans "Service" %}</h3>
                <div class="selected-service">
                    <strong>{{ service.title }}</strong>
                    <span class="service-info">{{ service.duration }} min • {{ service.price }}€</span>
                </div>
            </div>

            {# Step 2: Select Master (dynamic) #}
            <div class="booking-step">
                <h3>{% trans "Choose Master" %}</h3>
                <div
                    id="master-list"
                    hx-get="{% url 'htmx_masters_for_service' %}"
                    hx-params='{"service_id": "{{ service.id }}"}'
                    hx-trigger="load"
                    hx-target="#master-list"
                    hx-swap="innerHTML"
                >
                    <div class="loading">{% trans "Loading masters..." %}</div>
                </div>
            </div>

            {# Step 3: Select Time (hidden until master selected) #}
            <div class="booking-step" id="time-step" style="display:none;">
                <h3>{% trans "Choose Date & Time" %}</h3>
                <input
                    type="date"
                    id="date-picker"
                    hx-get="{% url 'htmx_time_slots' %}"
                    hx-include="[name='master_id'], [name='service_id']"
                    hx-target="#time-slots"
                    hx-trigger="change"
                >
                <div id="time-slots"></div>
            </div>

            {# Step 4: Client Info Form (hidden until time selected) #}
            <div class="booking-step" id="form-step" style="display:none;">
                <h3>{% trans "Your Details" %}</h3>
                <form method="POST" action="{% url 'booking_confirm' %}">
                    {% csrf_token %}
                    <input type="hidden" name="master_id" id="selected-master">
                    <input type="hidden" name="service_id" value="{{ service.id }}">
                    <input type="hidden" name="datetime_start" id="selected-time">

                    <input type="text" name="name" placeholder="{% trans 'Your Name' %}" required>
                    <input type="tel" name="phone" placeholder="{% trans 'Phone Number' %}" required>
                    <input type="email" name="email" placeholder="{% trans 'Email (optional)' %}">

                    <button type="submit" class="btn-pill">{% trans "Confirm Booking" %}</button>
                </form>
            </div>
        </div>
    </div>
</section>
{% endblock %}
```

#### HTMX Partial: Master List

```django
{# templates/booking/partials/_master_list.html #}
{% load static i18n %}

<div class="master-grid">
    {% for master in masters %}
    <button
        class="master-card"
        name="master_id"
        value="{{ master.id }}"
        hx-post="{% url 'htmx_select_master' %}"
        hx-vals='{"master_id": "{{ master.id }}", "service_id": "{{ service.id }}"}'
        hx-target="#time-step"
        hx-swap="outerHTML show:#time-step:top"
    >
        <img src="{{ master.photo.url }}" alt="{{ master.name }}">
        <h4>{{ master.name }}</h4>
        <p class="master-title">{{ master.title }}</p>
        <span class="experience">{{ master.years_experience }} {% trans "years" %}</span>
    </button>
    {% empty %}
    <p class="no-results">{% trans "No masters available for this service." %}</p>
    {% endfor %}
</div>

<script>
// Show time step when master selected
document.querySelectorAll('.master-card').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById('selected-master').value = btn.value;
        document.getElementById('time-step').style.display = 'block';
    });
});
</script>
```

#### HTMX Partial: Time Slots

```django
{# templates/booking/partials/_time_slots.html #}
{% load static i18n %}

{% if slots %}
<div class="time-grid">
    {% for slot in slots %}
    <button
        class="time-slot"
        data-time="{{ slot.datetime }}"
        onclick="selectTime('{{ slot.datetime }}')"
    >
        {{ slot.time_display }}
    </button>
    {% endfor %}
</div>
{% else %}
<p class="no-slots">{% trans "No available slots for this date." %}</p>
{% endif %}

<script>
function selectTime(datetime) {
    document.getElementById('selected-time').value = datetime;
    document.getElementById('form-step').style.display = 'block';
    document.getElementById('form-step').scrollIntoView({behavior: 'smooth'});
}
</script>
```

### URLs Configuration

```python
# features/booking/urls.py
from django.urls import path
from .views import booking_flow

urlpatterns = [
    # SEO pages
    path('services/<slug:service_slug>/book/', booking_flow.service_booking_page, name='service_booking'),
    path('team/<slug:master_slug>/book/', booking_flow.master_booking_page, name='master_booking'),

    # HTMX endpoints
    path('booking/htmx/masters/', booking_flow.htmx_masters_for_service, name='htmx_masters_for_service'),
    path('booking/htmx/services/', booking_flow.htmx_services_for_master, name='htmx_services_for_master'),
    path('booking/htmx/slots/', booking_flow.htmx_time_slots, name='htmx_time_slots'),

    # Final submit
    path('booking/confirm/', booking_flow.booking_confirm, name='booking_confirm'),
    path('booking/success/<str:token>/', booking_flow.booking_success, name='booking_success'),
]
```

## Dependencies

- **Requires:** TASK-101 (Master model with service_groups)
- **Requires:** TASK-201 (Appointment model)
- **Requires:** TASK-301 (Client model)
- **Requires:** TASK-203 (Time slot algorithm)
- **Blocks:** TASK-206 (Notifications)

## SEO Considerations

✅ **SEO-Friendly:**
- Initial page load is full HTML (server-rendered)
- HTMX swaps don't change URL (no hashbangs)
- Works without JavaScript (graceful degradation)
- Semantic HTML structure

❌ **Not SEO-indexed:**
- HTMX partial responses (intentional - they're not pages)

## Testing Checklist

- [ ] Service page loads with initial master list
- [ ] Selecting master loads time slots
- [ ] Date picker updates available times
- [ ] Form submission creates appointment and client
- [ ] Works without JavaScript (progressive enhancement)
- [ ] Mobile touch interactions work
- [ ] Loading states display correctly
- [ ] Error messages show for invalid selections

## Performance

- HTMX requests are <100ms (database queries optimized)
- Lazy loading for time slots (only fetch when needed)
- Cache master-service relationships (rarely change)

## Future Enhancements

- Add Alpine.js for client-side state management
- Implement WebSocket for real-time slot updates
- Add calendar view (month/week)
- Implement "smart suggest" (AI-powered slot recommendations)
{% endraw %}
