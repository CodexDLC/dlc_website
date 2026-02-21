# 📜 Contact Request Model (`contact_request.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This `contact_request.py` module defines the `ContactRequest` model, which represents submissions from the contact form on the Lily Website. It links contact requests to a `Client` and includes fields for the topic, message, processing status, and administrative notes.

## `ContactRequest` Model

The `ContactRequest` model (`ContactRequest(TimestampMixin, models.Model)`) stores information submitted through the contact form. It inherits from `TimestampMixin` for automatic timestamping.

### `TOPIC_CHOICES`

```python
TOPIC_GENERAL = "general"
TOPIC_BOOKING = "booking"
TOPIC_JOB = "job"
TOPIC_OTHER = "other"

TOPIC_CHOICES = [
    (TOPIC_GENERAL, _("General Question")),
    (TOPIC_BOOKING, _("Booking Inquiry")),
    (TOPIC_JOB, _("Job / Career")),
    (TOPIC_OTHER, _("Other")),
]
```
A list of tuples defining the available choices for the `topic` field, allowing users to categorize their contact requests.

### Fields

*   `client` (`ForeignKey` to `booking.Client`):
    Links the contact request to a `Client` model from the `booking` app.
    *   `on_delete=models.CASCADE`: If the client is deleted, their associated contact requests are also deleted.
    *   `related_name="contact_requests"`: Allows accessing contact requests from a client instance.
*   `topic` (`CharField`):
    The subject or topic of the contact request, chosen from `TOPIC_CHOICES`.
*   `message` (`TextField`):
    The detailed message submitted by the user.
*   `is_processed` (`BooleanField`):
    A flag indicating whether the contact request has been processed by an administrator.
*   `admin_notes` (`TextField`, optional):
    A field for administrators to add internal notes regarding the contact request.

### Meta Class

*   `verbose_name`, `verbose_name_plural`: Human-readable names for the model.
*   `ordering = ["-created_at"]`: Default ordering for contact requests (most recent first).

### `__str__()` Method

Returns a string representation of the contact request, including its primary key and the display name of its topic.
