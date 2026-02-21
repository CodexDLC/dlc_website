# 📜 Template Renderer

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This module defines the `TemplateRenderer` class, which provides a service for rendering templates using Jinja2. It is designed to load templates from a specified directory and render them with a given context, facilitating the generation of dynamic content like email bodies or HTML reports.

## `TemplateRenderer` Class

The `TemplateRenderer` encapsulates the Jinja2 environment and provides a simple interface for template rendering.

### Initialization (`__init__`)

```python
def __init__(self, templates_dir: str):
```
Initializes the Jinja2 environment.

*   `templates_dir` (`str`): The absolute path to the directory containing the templates.

**Process:**
1.  **Directory Validation:** Checks if the `templates_dir` exists. If not, it logs an error and raises a `FileNotFoundError`.
2.  **Jinja2 Environment Setup:** Initializes a Jinja2 `Environment` with a `FileSystemLoader` pointing to the `templates_dir`. `select_autoescape(["html", "xml"])` is used to automatically escape HTML and XML content, preventing cross-site scripting (XSS) vulnerabilities.
3.  **Logging:** Logs an informational message upon successful initialization.

### `render` Method

```python
def render(self, template_name: str, context: dict) -> str:
```
Renders a specified template with the provided context data.

*   `template_name` (`str`): The name of the template file (e.g., `"email_notification.html"`).
*   `context` (`dict`): A dictionary containing the data to be passed to the template for rendering.

**Process:**
1.  **Template Loading:** Retrieves the template by `template_name` from the Jinja2 environment.
2.  **Rendering:** Renders the template using the provided `context`.
3.  **Error Handling:** Catches and logs any exceptions that occur during the rendering process, then re-raises the exception.

**Returns:**
`str`: The rendered content of the template as a string.
