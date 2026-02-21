from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger as log


class GarbageStateRegistry:
    """
    Реестр состояний, в которых текстовые сообщения считаются мусором и должны удаляться.
    Наполняется динамически при загрузке фич.
    """

    _states: set[str] = set()

    @classmethod
    def register(cls, state):
        """
        Регистрирует стейт (объект State, строку или список/группу) как мусорный.
        """
        if isinstance(state, list | tuple | set):
            for s in state:
                cls.register(s)
            return

        # Если это StatesGroup (класс), берем все его стейты
        if hasattr(state, "__states__"):
            for s in state.__states__:
                cls.register(s)
            return

        # Если это State объект или строка
        state_name = state.state if hasattr(state, "state") else str(state)
        cls._states.add(state_name)
        log.debug(f"GarbageRegistry | registered='{state_name}'")

    @classmethod
    def is_garbage(cls, state_name: str | None) -> bool:
        return state_name in cls._states


class IsGarbageStateFilter(Filter):
    """
    Фильтр aiogram, проверяющий наличие текущего стейта в GarbageStateRegistry.
    """

    async def __call__(self, message: Message, state: FSMContext) -> bool:
        current_state = await state.get_state()
        return GarbageStateRegistry.is_garbage(current_state)
