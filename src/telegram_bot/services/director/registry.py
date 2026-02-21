"""
Реестр маршрутов для Director.
Определяет межфичевые (SCENE_ROUTES) и внутрифичевые (RENDER_ROUTES) переходы.
"""

from typing import NamedTuple

from aiogram.fsm.state import State


class SceneConfig(NamedTuple):
    """Конфигурация сцены: FSM стейт + entry-point сервис."""

    fsm_state: State
    entry_service: str  # Ключ в RENDER_ROUTES[feature] для entry point


# =============================================================================
# SCENE_ROUTES: Межфичевые переходы (смена FSM State)
# Добавляйте маршруты при создании новых фич.
# =============================================================================
SCENE_ROUTES: dict[str, SceneConfig] = {}


# =============================================================================
# RENDER_ROUTES: Внутрифичевые переходы (без смены FSM State)
# feature -> service_key -> container_getter
# =============================================================================
RENDER_ROUTES: dict[str, dict[str, str]] = {}
