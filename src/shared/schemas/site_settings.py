from typing import Any

from pydantic import BaseModel, Field


class SiteSettingsSchema(BaseModel):
    """
    Pydantic-схема для настроек сайта.
    Обеспечивает типизацию и валидацию данных из Redis.

    Все поля загружаются из Redis (через SiteSettingsManager).
    Дефолты используются как fallback если данных в Redis нет.
    Заполни значения через Django Admin или напрямую в Redis.
    """

    company_name: str = Field(default="My Company")
    site_base_url: str = Field(default="http://localhost:8000/")

    # Используем PNG версию для 100% совместимости в Email
    logo_url: str = Field(default="/static/img/logo.png")

    # Контакты
    phone: str = Field(default="")
    email: str = Field(default="")
    address_street: str = Field(default="")
    address_locality: str = Field(default="")
    address_postal_code: Any = Field(default="")

    # Гео
    latitude: Any = Field(default="")
    longitude: Any = Field(default="")

    # Соцсети
    instagram_url: str = Field(default="")
    telegram_url: str | None = None
    whatsapp_url: str | None = None

    # Часы работы (строки для отображения)
    working_hours_weekdays: str = Field(default="09:00 - 18:00")
    working_hours_saturday: str = Field(default="10:00 - 14:00")
    working_hours_sunday: str = Field(default="Closed")

    # Технические пути
    url_path_contact_form: str = Field(default="/contacts/")
    url_path_confirm: str = Field(default="/appointments/confirm/{token}/")
    url_path_cancel: str = Field(default="/appointments/cancel/{token}/")
    url_path_reschedule: str = Field(default="/booking/")

    # Прочее
    price_range: str = Field(default="$$")
