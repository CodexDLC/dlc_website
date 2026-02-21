# 📜 Legal Views (`legal.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This `legal.py` module defines Django views for various legal and informational pages of the Lily Website. It uses Django's generic `TemplateView` to render static HTML templates for pages like Impressum (Imprint), Datenschutz (Privacy Policy), and FAQ.

## Purpose

The views in this module are responsible for serving essential legal and informational content, ensuring that the website complies with legal requirements and provides necessary information to users.

## `ImpressumView` Class

```python
class ImpressumView(TemplateView):
    template_name = "legal/impressum.html"
```
This view renders the Impressum (Imprint) page.

*   `template_name = "legal/impressum.html"`: Specifies the HTML template to be used for the Impressum page.

## `DatenschutzView` Class

```python
class DatenschutzView(TemplateView):
    template_name = "legal/datenschutz.html"
```
This view renders the Datenschutz (Privacy Policy) page.

*   `template_name = "legal/datenschutz.html"`: Specifies the HTML template to be used for the Privacy Policy page.

## `FaqView` Class

```python
class FaqView(TemplateView):
    template_name = "legal/faq.html"
```
This view renders the FAQ (Frequently Asked Questions) page.

*   `template_name = "legal/faq.html"`: Specifies the HTML template to be used for the FAQ page.

## Usage

These views are typically mapped to specific URL patterns in the `main` feature's `urls.py` (e.g., `/legal/impressum`, `/legal/datenschutz`, `/legal/faq`). They are designed to serve static content without requiring complex backend logic.
