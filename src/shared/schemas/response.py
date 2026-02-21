from pydantic import BaseModel


class ResponseHeader(BaseModel):
    """
    Метаданные ответа.
    Управляют состоянием бота и сообщают об ошибках.
    """

    success: bool = True
    message: str | None = None

    # Откуда мы пришли (для логирования / навигации)
    current_state: str | None = None

    # Куда переключить FSM (если None - остаемся где были)
    next_state: str | None = None

    # Trace ID для логов
    trace_id: str | None = None


class CoreResponseDTO[T](BaseModel):
    """
    Стандартный ответ: Заголовок + Данные.
    Используется для обмена данными между слоями (Client -> Orchestrator).
    """

    header: ResponseHeader
    payload: T | None = None
