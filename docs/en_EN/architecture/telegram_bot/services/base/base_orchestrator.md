# 📜 Base Orchestrator

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `BaseBotOrchestrator` class, which serves as a foundational abstract class for all feature orchestrators within the Telegram bot application. It establishes a contract for the lifecycle of a feature, including entry point handling, data rendering, and processing API responses.

## `BaseBotOrchestrator` Class

The `BaseBotOrchestrator` provides a standardized structure for managing the flow of control and data within a specific bot feature. It integrates with the `Director` service for scene management and handles the transformation of business data into UI-ready `UnifiedViewDTO` objects.

### Initialization (`__init__`)

```python
def __init__(self, expected_state: str | None):
```
Initializes the `BaseBotOrchestrator`.

*   `expected_state` (`str | None`): An optional string representing the expected FSM state for this orchestrator. This is used for navigation checks when processing API responses.

**Key Actions:**
*   Sets `self.expected_state`.
*   Initializes `self._director` to `None`, which will be set later by the `Director` service.

### `set_director` Method

```python
def set_director(self, director: "Director") -> None:
```
Sets the `Director` instance for the orchestrator. This method is called by the `Director` itself during the application setup.

*   `director` (`Director`): The global `Director` service instance.

### `director` Property

```python
@property
def director(self) -> "Director":
```
A property that provides access to the `Director` instance. It raises a `RuntimeError` if the `Director` has not been set, ensuring that orchestrators always have access to this critical service.

### `handle_entry` Method

```python
async def handle_entry(self, user_id: int, payload: Any = None) -> UnifiedViewDTO:
```
This asynchronous method is the primary entry point for a feature (cold start). It is called by the `Director` when a user enters a feature, especially when initial data needs to be loaded.

*   `user_id` (`int`): The ID of the user.
*   `payload` (`Any | None`): Optional initial data or context passed to the feature.

**Purpose:**
To load necessary data and then call `self.render()`. The default implementation simply calls `render()` with the provided payload.

**Returns:**
`UnifiedViewDTO`: A DTO containing the UI elements to be displayed.

### `render_content` Method

```python
async def render_content(self, payload: Any) -> Any:
```
An abstract asynchronous method that *must* be implemented by concrete orchestrator subclasses. Its responsibility is to transform business data (`payload`) into a `ViewResultDTO` for the main content area.

*   `payload` (`Any`): The business data to be rendered.

**Raises:**
`NotImplementedError`: If not implemented by a subclass.

### `render` Method

```python
async def render(self, payload: Any) -> UnifiedViewDTO:
```
The main rendering method (hot start). It is called by the `Director` when the `payload` (e.g., an API response) is already available.

*   `payload` (`Any`): The data to be rendered, which can be a `CoreResponseDTO` or any other business data.

**Process:**
1.  **Process API Response:** If `payload` is a `CoreResponseDTO`, it calls `process_response()`.
2.  **Render Content:** Otherwise, it calls `render_content()` with the `payload` to get the UI for the main content.
3.  **Create UnifiedViewDTO:** Wraps the `content_view` in a `UnifiedViewDTO`.

**Returns:**
`UnifiedViewDTO`: A DTO containing the UI elements to be displayed.

### `process_response` Method

```python
async def process_response(self, response: CoreResponseDTO) -> UnifiedViewDTO:
```
A universal method for processing `CoreResponseDTO` objects received from a backend API. It handles navigation and content rendering based on the response.

*   `response` (`CoreResponseDTO`): The response object from the backend API.

**Process:**
1.  **Navigation Check:** If `response.header.next_state` is present and different from `self.expected_state`, it means the backend is requesting a scene change. The orchestrator delegates this to the `director.set_scene()`.
2.  **Content Render:** If no navigation change is requested, and `response.payload` is present, it calls `render_content()` with the `response.payload` to generate the UI.
3.  **Create UnifiedViewDTO:** Constructs a `UnifiedViewDTO` with the rendered content.

**Returns:**
`UnifiedViewDTO`: A DTO containing the UI elements to be displayed, potentially after a scene change.
