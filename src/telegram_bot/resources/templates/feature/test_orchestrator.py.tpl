import pytest
from unittest.mock import AsyncMock, MagicMock

from src.telegram_bot.features.{feature_key}.logic.orchestrator import {class_name}Orchestrator
from src.telegram_bot.features.{feature_key}.feature_setting import {class_name}States

@pytest.mark.asyncio
async def test_handle_entry():
    # Arrange
    orchestrator = {class_name}Orchestrator()
    orchestrator.set_director(AsyncMock()) # Mock Director

    # Act
    view = await orchestrator.handle_entry(user_id=123)

    # Assert
    assert view.content is not None
    # Проверяем, что стейт переключился (если логика это подразумевает)
    # orchestrator.director.state.set_state.assert_called_with({class_name}States.main)
