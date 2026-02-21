from pydantic import BaseModel, ConfigDict


class UserUpsertDTO(BaseModel):
    """
    DTO для создания или обновления пользователя (из Telegram).
    """

    telegram_id: int
    first_name: str
    username: str | None = None
    last_name: str | None = None
    language_code: str | None = None
    is_premium: bool = False

    model_config = ConfigDict(from_attributes=True)
