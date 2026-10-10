# Task: Email Preview with LLM Enhancement

## Objective
Implement a "Preview" feature for the Compose page that allows staff to see how the email will look to the recipient before sending.

## Requirements
- **LLM Integration**: Use a language model to:
    - Automatically format the plain text body into a structured, professional email.
    - Translate the content if the recipient's language differs from the sender's.
    - Apply a consistent "Factor" brand voice to the message.
- **Template System**:
    - Use the site's email HTML templates to wrap the message.
    - Show proof of layout (headers, footers, typography).
- **UI/UX**:
    - Trigger preview from the "Preview" button in `compose.html`.
    - Display the preview in a modal or a separate side panel.
    - Allow the user to "Apply" the LLM-suggested formatting back to the editor.

## Implementation Steps
1. [ ] Create a `PreviewView` in `cabinet.views.conversations`.
2. [ ] Integrate with an LLM service (e.g., via a utility in `core.llm`).
3. [ ] Design/select the HTML template for the preview.
4. [ ] Implement the frontend logic to fetch and display the preview without reloading the page.
