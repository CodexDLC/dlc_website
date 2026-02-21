# 📜 Base Manager

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `BaseStateManager` class, which serves as a foundational component for managing FSM (Finite State Machine) states within the Telegram bot. It provides a structured way to store and retrieve feature-specific data within the Aiogram FSM context, ensuring data isolation and simplifying state management logic.

## `BaseStateManager` Class

The `BaseStateManager` is an abstract manager designed to encapsulate the common operations for handling temporary data (drafts) associated with a particular feature.

### Initialization (`__init__`)

```python
def __init__(self, state: FSMContext, feature_key: str):
```
Initializes the `BaseStateManager`.

*   `state` (`FSMContext`): The Aiogram FSM context for the current user.
*   `feature_key` (`str`): A unique string identifier for the feature. This key is used to create a dedicated storage namespace within the FSM data, preventing conflicts between different features.

**Key Action:**
*   Sets `self.storage_key` to `f"draft:{feature_key}"`, which will be the key under which this feature's data is stored in the FSM.

### `get_payload` Method

```python
async def get_payload(self) -> dict[str, Any]:
```
Asynchronously retrieves all data associated with the feature's draft.

**Returns:**
`dict[str, Any]`: A dictionary containing all the draft data for the feature. Returns an empty dictionary if no data is found for the `storage_key`.

### `update` Method

```python
async def update(self, **kwargs: Any) -> dict[str, Any]:
```
Asynchronously updates the feature's draft with the provided key-value pairs. This method performs a partial update, merging new data with existing data.

*   `**kwargs` (`Any`): Arbitrary keyword arguments representing the fields and their new values to update in the draft.

**Process:**
1.  Retrieves the current draft data using `get_payload()`.
2.  Updates the current data with the new `kwargs`.
3.  Saves the updated data back into the FSM under `self.storage_key`.

**Returns:**
`dict[str, Any]`: The updated dictionary of the feature's draft data.

### `clear` Method

```python
async def clear(self) -> None:
```
Asynchronously clears all draft data associated with the feature.

**Process:**
*   Sets the value of `self.storage_key` in the FSM to an empty dictionary, effectively removing all stored draft data for the feature.

### `set_value` Method

```python
async def set_value(self, key: str, value: Any) -> None:
```
Asynchronously sets a specific key-value pair within the feature's draft.

*   `key` (`str`): The key of the value to set.
*   `value` (`Any`): The value to store.

**Process:**
*   Internally calls `update()` with the single key-value pair.

### `get_value` Method

```python
async def get_value(self, key: str, default: Any = None) -> Any:
```
Asynchronously retrieves a specific value from the feature's draft.

*   `key` (`str`): The key of the value to retrieve.
*   `default` (`Any`): The default value to return if the key is not found in the draft (default: `None`).

**Process:**
1.  Retrieves the entire draft payload using `get_payload()`.
2.  Returns the value associated with the `key` from the payload, or the `default` value if the key is not present.
