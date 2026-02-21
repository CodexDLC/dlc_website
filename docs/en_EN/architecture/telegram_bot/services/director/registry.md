# 📜 Registry

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the routing registries (`SCENE_ROUTES` and `RENDER_ROUTES`) used by the `Director` service to manage transitions between features and within features. It also defines a `SceneConfig` NamedTuple for structuring scene configurations.

## `SceneConfig` NamedTuple

```python
class SceneConfig(NamedTuple):
    fsm_state: State
    entry_service: str
```
A `NamedTuple` used to define the configuration for a specific scene (feature).

*   `fsm_state` (`State`): The Aiogram FSM state associated with this scene.
*   `entry_service` (`str`): The key of the entry-point service within the feature's `RENDER_ROUTES` that should be called when entering this scene.

## `SCENE_ROUTES`

```python
SCENE_ROUTES: dict[str, SceneConfig] = {}
```
A dictionary that maps feature keys (strings) to `SceneConfig` objects. This registry defines **inter-feature transitions**, meaning transitions that involve a change in the user's FSM state.

**Purpose:**
When the `Director` initiates a scene change, it looks up the target feature in `SCENE_ROUTES` to determine the FSM state to set and the entry-point service to call.

**Usage:**
New features should add their scene configurations to this dictionary.

## `RENDER_ROUTES`

```python
RENDER_ROUTES: dict[str, dict[str, str]] = {}
```
A nested dictionary that defines **intra-feature transitions** (without changing the FSM state). It maps a feature key to another dictionary, which in turn maps a service key to a container getter string.

**Purpose:**
This registry is used for transitions or actions that occur within the same feature, where the FSM state remains unchanged. It allows for dynamic resolution of services or orchestrators based on the feature and a specific service key.

**Usage:**
This can be used to define different rendering paths or sub-components within a feature.
