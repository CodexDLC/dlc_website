# 📜 Animation Service

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `UIAnimationService` class, which provides functionalities for displaying various types of loading and waiting animations in the Telegram bot's interface. It integrates with the `ViewSender` to update messages dynamically, enhancing user experience during asynchronous operations.

## `AnimationType` Enum

```python
class AnimationType(Enum):
    PROGRESS_BAR = "progress_bar"
    INFINITE = "infinite"
    NONE = "none"
```
An enumeration defining the types of animations that can be displayed.

*   `PROGRESS_BAR`: A progress bar that fills up from 0% to 100%.
*   `INFINITE`: An infinite "snake" or running indicator.
*   `NONE`: No animation is displayed.

## `PollerFunc` Type Alias

```python
PollerFunc = Callable[[], Awaitable[tuple[UnifiedViewDTO, bool]]]
```
A type alias for an asynchronous callable that takes no arguments and returns a tuple containing a `UnifiedViewDTO` and a boolean indicating whether the polling should continue (`True`) or stop (`False`).

## `UIAnimationService` Class

The `UIAnimationService` orchestrates different animation scenarios, such as showing a loading indicator during data fetching, polling for status updates, or displaying progress for timed operations.

### Initialization (`__init__`)

```python
def __init__(self, sender: ViewSender):
```
Initializes the `UIAnimationService`.

*   `sender` (`ViewSender`): An instance of `ViewSender` used to send and edit messages in Telegram.

### Core Methods

#### `run_delayed_fetch` Method

```python
async def run_delayed_fetch(
    self,
    fetch_func: PollerFunc,
    delay: float = 3.0,
    step_interval: float = 1.0,
    loading_text: str = "🔍 <b>Поиск...</b>",
    animation_type: AnimationType = AnimationType.PROGRESS_BAR,
) -> None:
```
This method runs an animation for a specified `delay` duration, and then performs a single data fetch at the end. It's suitable for operations like search or scanning where a single backend request is made after a short wait.

*   `fetch_func` (`PollerFunc`): An asynchronous function that will be called once at the end of the animation to fetch data. It should return a `UnifiedViewDTO` and a boolean (though the boolean is ignored here).
*   `delay` (`float`): The total duration of the animation in seconds.
*   `step_interval` (`float`): The interval between animation frames in seconds.
*   `loading_text` (`str`): The base text to display during the animation.
*   `animation_type` (`AnimationType`): The type of animation to display (e.g., `PROGRESS_BAR`, `INFINITE`).

**Process:**
1.  Displays an animation for `delay` seconds, updating the animation frame every `step_interval`.
2.  After the animation, calls `fetch_func` once.
3.  Sends the final `UnifiedViewDTO` returned by `fetch_func`.

#### `run_polling_loop` Method

```python
async def run_polling_loop(
    self,
    check_func: PollerFunc,
    timeout: float = 60.0,
    step_interval: float = 2.0,
    loading_text: str = "⏳ <b>Ожидание...</b>",
    animation_type: AnimationType = AnimationType.INFINITE,
) -> None:
```
This method continuously polls a `check_func` until a condition is met or a `timeout` is reached. It's used for scenarios like waiting for combat results or arena queues, where the bot repeatedly checks a status.

*   `check_func` (`PollerFunc`): An asynchronous function that returns a `UnifiedViewDTO` and a boolean (`is_waiting`). The loop continues as long as `is_waiting` is `True`.
*   `timeout` (`float`): The maximum time to wait for the condition to be met, in seconds.
*   `step_interval` (`float`): The interval between calls to `check_func` and animation updates.
*   `loading_text` (`str`): The base text to display during the polling.
*   `animation_type` (`AnimationType`): The type of animation to display (typically `INFINITE`).

**Process:**
1.  Repeatedly calls `check_func` at `step_interval`.
2.  If `check_func` indicates `is_waiting=True`, it updates the animation in the `UnifiedViewDTO` and sends it.
3.  The loop exits when `is_waiting` becomes `False` or `timeout` is reached.

#### `run_timed_polling` Method

```python
async def run_timed_polling(
    self,
    check_func: PollerFunc,
    duration: float = 5.0,
    step_interval: float = 1.0,
    loading_text: str = "🚶 <b>Перемещение...</b>",
    animation_type: AnimationType = AnimationType.PROGRESS_BAR,
) -> None:
```
This method performs an initial check, then displays a progress bar animation for a specified `duration`, and continues polling if the operation is still ongoing. It's suitable for operations that have an expected duration, like character movement, where the result might be stored in Redis.

*   `check_func` (`PollerFunc`): An asynchronous function that returns a `UnifiedViewDTO` and a boolean (`is_waiting`).
*   `duration` (`float`): The expected duration of the operation in seconds, used for the progress bar.
*   `step_interval` (`float`): The interval between animation frames and checks.
*   `loading_text` (`str`): The base text to display during the animation.
*   `animation_type` (`AnimationType`): The type of animation to display (typically `PROGRESS_BAR`).

**Process:**
1.  Performs an initial check using `check_func`.
2.  Displays a `PROGRESS_BAR` animation for `duration` seconds.
3.  If `check_func` still indicates `is_waiting=True` after `duration`, it transitions to an `INFINITE` animation mode and continues polling indefinitely until `is_waiting` becomes `False`.

### Atomic Helpers (Private Methods)

#### `_poll_check` Method

```python
async def _poll_check(self, func: PollerFunc) -> tuple[UnifiedViewDTO, bool]:
```
Executes the provided polling function (`func`) and ensures its return value is a `(UnifiedViewDTO, bool)` tuple.

*   `func` (`PollerFunc`): The polling function to execute.

**Returns:**
`tuple[UnifiedViewDTO, bool]`: The result of the polling function.

#### `_inject_animation` Method

```python
def _inject_animation(self, view_dto: UnifiedViewDTO, anim_str: str) -> None:
```
Injects the generated animation string into the `text` of the `UnifiedViewDTO`'s content. If the content text contains `{ANIMATION}`, it replaces it; otherwise, it appends the animation string.

*   `view_dto` (`UnifiedViewDTO`): The DTO to modify.
*   `anim_str` (`str`): The animation string to inject.

#### `_send` Method

```python
async def _send(self, view_dto: UnifiedViewDTO) -> None:
```
Sends the `UnifiedViewDTO` using the `ViewSender` instance.

*   `view_dto` (`UnifiedViewDTO`): The DTO to send.

#### `_create_temp_content` Method

```python
def _create_temp_content(self, text: str):
```
Creates a temporary `ViewResultDTO` with the given text, used for displaying animation frames.

*   `text` (`str`): The text content for the temporary `ViewResultDTO`.

**Returns:**
`ViewResultDTO`: A new `ViewResultDTO` instance.

### Animation Generators (Private Methods)

#### `_generate_animation` Method

```python
def _generate_animation(self, step: int, total_steps: int, text: str, animation_type: AnimationType) -> str:
```
Generates the animation string based on the specified `animation_type`.

*   `step` (`int`): The current step in the animation sequence.
*   `total_steps` (`int`): The total number of steps for `PROGRESS_BAR` animation.
*   `text` (`str`): The base text to include in the animation string.
*   `animation_type` (`AnimationType`): The type of animation to generate.

**Returns:**
`str`: The generated animation string.

#### `_gen_infinite_bar` Method

```python
def _gen_infinite_bar(self, step: int, text: str) -> str:
```
Generates an infinite "snake" or running indicator animation string.

*   `step` (`int`): The current step, used to determine the position of the indicator.
*   `text` (`str`): The base text.

**Returns:**
`str`: The infinite bar animation string (e.g., "Text [□■□□□]").

#### `_gen_progress_bar` Method

```python
def _gen_progress_bar(self, step: int, total_steps: int, text: str) -> str:
```
Generates a progress bar animation string.

*   `step` (`int`): The current step in the progress.
*   `total_steps` (`int`): The total number of steps for the progress bar.
*   `text` (`str`): The base text.

**Returns:**
`str`: The progress bar animation string (e.g., "Text [■■□□□] 40%").
