{% raw %}
# 📜 Base Email Template (`base_email.html`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

The `base_email.html` is a Jinja2 base template providing the foundational HTML structure for all email notifications. It defines the layout, styling, header and footer — child templates only override the `{% block content %}` block.

## Structure

### Header
- Background color: `#2c3e50` (TODO: replace with your brand color)
- Displays `{{ logo_url }}` linked to `{{ site_url }}`
- Alt text uses `{{ company_name }}`

### Content Block
```html
{% block content %}{% endblock %}
```
Override this in every child template to inject specific email content.

### Footer
- Displays copyright: `© {{ company_name }}`
- Link to `{{ site_url }}` (Website)
- Optional link to `{{ contact_form_url }}` (Contact) — shown only if not `#`
- Standard "automated email" disclaimer

## Jinja2 Variables

| Variable           | Source                        | Description                         |
|--------------------|-------------------------------|-------------------------------------|
| `company_name`     | `SiteSettingsSchema`          | Your company name                   |
| `site_url`         | `SiteSettingsSchema`          | Base URL of the website             |
| `logo_url`         | `NotificationService._enrich_context` | Full URL to logo image        |
| `contact_form_url` | `NotificationService._enrich_context` | URL to contact form (or `#`) |

## Creating a New Template

1. Create `src/workers/templates/your_template.html`
2. Start with `{% extends "base_email.html" %}`
3. Override `{% block title %}` and `{% block content %}`
4. Call `send_email_task` with `template_name="your_template.html"`

See `example_notification.html` for a working example.
{% endraw %}
