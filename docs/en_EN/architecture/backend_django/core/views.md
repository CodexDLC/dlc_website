# 📜 Project-Wide Views (`views.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `views.py` file contains project-wide views that are not specific to any particular feature. Currently, it defines `LLMSTextView`, a specialized view for serving language-specific `llms.txt` files, which are used to control how Large Language Models (LLMs) or AI crawlers interact with the website.

## `LLMSTextView` Class

The `LLMSTextView` is a Django `TemplateView` subclass designed to serve a `llms.txt` file, similar to how `robots.txt` is served, but with support for internationalization.

### Attributes

*   `content_type = "text/plain"`:
    Sets the HTTP `Content-Type` header for the response to `text/plain`, indicating that the content is plain text.

### `get_template_names()` Method

```python
def get_template_names(self):
    current_language = translation.get_language()
    return [f"llms_{current_language}.txt"]
```

### Description

This method dynamically determines the name of the template to render based on the currently active language.

### Process

1.  `current_language = translation.get_language()`: Retrieves the currently active language code (e.g., "de", "en", "ru").
2.  `return [f"llms_{current_language}.txt"]`: Constructs a list containing a single template name in the format `llms_{language_code}.txt` (e.g., `llms_de.txt`).

### `render_to_response()` Method

```python
def render_to_response(self, context, **response_kwargs):
    # Ensure the template exists for the current language
    try:
        return super().render_to_response(context, **response_kwargs)
    except TemplateDoesNotExist:
        # Fallback to default language (e.g., German) if specific language template not found
        return TemplateView.as_view(template_name=f"llms_{settings.LANGUAGE_CODE}.txt", content_type="text/plain")(
            self.request
        )
```

### Description

This method is overridden to provide a fallback mechanism if a language-specific `llms.txt` template is not found.

### Process

1.  **Attempt to Render:** It first attempts to render the template determined by `get_template_names()` using `super().render_to_response()`.
2.  **Fallback on `TemplateDoesNotExist`:** If a `TemplateDoesNotExist` exception occurs (meaning the language-specific template was not found), it falls back to rendering a template for the default language defined in `settings.LANGUAGE_CODE` (e.g., `llms_de.txt`). This ensures that an `llms.txt` file is always served, even if a translation is missing.

## Usage

This view is typically mapped to a URL pattern like `/llms.txt` in the root `urls.py` (as seen in `core/urls.py`). It allows website administrators to provide specific instructions to LLMs and AI crawlers, similar to how `robots.txt` is used for traditional search engine crawlers.
