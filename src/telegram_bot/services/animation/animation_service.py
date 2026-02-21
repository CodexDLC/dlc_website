import asyncio
from collections.abc import Awaitable, Callable
from enum import Enum

from src.telegram_bot.services.base.view_dto import UnifiedViewDTO
from src.telegram_bot.services.sender.view_sender import ViewSender


class AnimationType(Enum):
    """Тип анимации для отображения прогресса."""

    PROGRESS_BAR = "progress_bar"  # Заполняется от 0% до 100%
    INFINITE = "infinite"  # Бегущий индикатор (змейка)
    NONE = "none"  # Без анимации


# Type alias для check_func
PollerFunc = Callable[[], Awaitable[tuple[UnifiedViewDTO, bool]]]


class UIAnimationService:
    """
    Сервис для анимации ожидания (Polling).

    Три основных сценария:
    - run_delayed_fetch: анимация N секунд → один запрос
    - run_polling_loop: цикл запросов до события
    - run_timed_polling: запрос сразу → анимация по duration из результата
    """

    def __init__(self, sender: ViewSender):
        self.sender = sender

    # =========================================================================
    # Core Methods (New API)
    # =========================================================================

    async def run_delayed_fetch(
        self,
        fetch_func: PollerFunc,
        delay: float = 3.0,
        step_interval: float = 1.0,
        loading_text: str = "🔍 <b>Поиск...</b>",
        animation_type: AnimationType = AnimationType.PROGRESS_BAR,
    ) -> None:
        """
        Сценарий: Анимация N секунд → один запрос в конце.

        Используется для: Search, Scan — показываем анимацию,
        потом делаем один запрос к backend.

        Args:
            fetch_func: Функция для получения данных (вызывается один раз в конце)
            delay: Общая длительность анимации в секундах
            step_interval: Интервал между кадрами анимации
            loading_text: Текст для отображения во время анимации
            animation_type: Тип анимации (PROGRESS_BAR или INFINITE)
        """
        steps = max(1, int(delay / step_interval))

        # Фаза анимации
        for i in range(steps):
            # Создаём временный view для анимации
            anim_str = self._generate_animation(i, steps, loading_text, animation_type)
            temp_view = UnifiedViewDTO(content=self._create_temp_content(anim_str))
            await self._send(temp_view)
            await asyncio.sleep(step_interval)

        # Финальный запрос
        view_dto, _ = await self._poll_check(fetch_func)
        await self._send(view_dto)

    async def run_polling_loop(
        self,
        check_func: PollerFunc,
        timeout: float = 60.0,
        step_interval: float = 2.0,
        loading_text: str = "⏳ <b>Ожидание...</b>",
        animation_type: AnimationType = AnimationType.INFINITE,
    ) -> None:
        """
        Сценарий: Цикл запросов до события.

        Используется для: Combat polling, Arena waiting —
        делаем запросы каждые N секунд, пока is_waiting=True.

        Args:
            check_func: Функция проверки статуса, возвращает (view, is_waiting)
            timeout: Максимальное время ожидания в секундах
            step_interval: Интервал между проверками
            loading_text: Текст для отображения во время ожидания
            animation_type: Тип анимации (обычно INFINITE)
        """
        steps = int(timeout / step_interval)

        for i in range(steps):
            # 1. Check
            view_dto, is_waiting = await self._poll_check(check_func)

            # 2. Animate (если ждём)
            if is_waiting and view_dto.content:
                anim_str = self._generate_animation(i, steps, loading_text, animation_type)
                self._inject_animation(view_dto, anim_str)

            # 3. Send
            await self._send(view_dto)

            # 4. Exit or Sleep
            if not is_waiting:
                return

            await asyncio.sleep(step_interval)

    async def run_timed_polling(
        self,
        check_func: PollerFunc,
        duration: float = 5.0,
        step_interval: float = 1.0,
        loading_text: str = "🚶 <b>Перемещение...</b>",
        animation_type: AnimationType = AnimationType.PROGRESS_BAR,
    ) -> None:
        """
        Сценарий: Запрос сразу → анимация по duration из результата.

        Используется для: Move — запрос уходит в background сразу,
        результат хранится в Redis, показываем Progress Bar по времени.

        Args:
            check_func: Функция проверки, которая читает результат из state/Redis
            duration: Ожидаемая длительность анимации
            step_interval: Интервал между кадрами
            loading_text: Текст для отображения
            animation_type: Тип анимации (PROGRESS_BAR для timed)
        """
        steps = max(1, int(duration / step_interval))

        # Фаза Progress Bar
        for i in range(steps):
            view_dto, is_waiting = await self._poll_check(check_func)

            if not is_waiting:
                await self._send(view_dto)
                return

            anim_str = self._generate_animation(i, steps, loading_text, animation_type)
            self._inject_animation(view_dto, anim_str)

            await self._send(view_dto)
            await asyncio.sleep(step_interval)

        # Overflow: Backend slow response → Infinite mode
        infinite_step = 0
        while True:
            view_dto, is_waiting = await self._poll_check(check_func)

            if not is_waiting:
                await self._send(view_dto)
                return

            anim_str = self._generate_animation(infinite_step, steps, loading_text, AnimationType.INFINITE)
            self._inject_animation(view_dto, anim_str)

            await self._send(view_dto)
            await asyncio.sleep(step_interval)
            infinite_step += 1

    # =========================================================================
    # Atomic Helpers (Private)
    # =========================================================================

    async def _poll_check(self, func: PollerFunc) -> tuple[UnifiedViewDTO, bool]:
        """Выполняет проверку статуса."""
        result = await func()
        if isinstance(result, tuple):
            return result
        return result, False

    def _inject_animation(self, view_dto: UnifiedViewDTO, anim_str: str) -> None:
        """Вставляет строку анимации в контент."""
        if not view_dto.content:
            return

        if "{ANIMATION}" in view_dto.content.text:
            view_dto.content.text = view_dto.content.text.replace("{ANIMATION}", anim_str)
        else:
            view_dto.content.text += f"\n\n{anim_str}"

    async def _send(self, view_dto: UnifiedViewDTO) -> None:
        """Отправляет View."""
        await self.sender.send(view_dto)

    def _create_temp_content(self, text: str):
        """Создаёт временный ViewResultDTO для анимации."""
        from src.telegram_bot.services.base.view_dto import ViewResultDTO

        return ViewResultDTO(text=text)

    # =========================================================================
    # Animation Generators
    # =========================================================================

    def _generate_animation(self, step: int, total_steps: int, text: str, animation_type: AnimationType) -> str:
        """Генерирует строку анимации в зависимости от типа."""
        if animation_type == AnimationType.PROGRESS_BAR:
            return self._gen_progress_bar(step, total_steps, text)
        elif animation_type == AnimationType.INFINITE:
            return self._gen_infinite_bar(step, text)
        else:
            return text

    def _gen_infinite_bar(self, step: int, text: str) -> str:
        """Бегущий индикатор: [■□□□□] -> [□■□□□] -> ..."""
        total_chars = 10
        position = step % total_chars
        bar = "□" * position + "■" + "□" * (total_chars - position - 1)
        return f"{text} [{bar}]"

    def _gen_progress_bar(self, step: int, total_steps: int, text: str) -> str:
        """Заполняющийся индикатор: [■■□□□] 40%"""
        percent = 1.0 if total_steps == 0 else step / total_steps

        total_chars = 10
        filled = int(total_chars * percent)
        empty = total_chars - filled

        bar = "■" * filled + "□" * empty
        return f"{text} [{bar}] {int(percent * 100)}%"
