from datetime import datetime, timedelta
from urllib.parse import quote

from src.workers.core.email_client import AsyncEmailClient
from src.workers.core.template_renderer import TemplateRenderer


class NotificationService:
    def __init__(
        self,
        templates_dir: str,
        site_url: str,
        logo_url: str | None = None,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        smtp_from_email: str | None = None,
        smtp_use_tls: bool = False,
        url_path_confirm: str | None = None,
        url_path_cancel: str | None = None,
        url_path_reschedule: str | None = None,
        url_path_contact_form: str | None = None,
        address: str = "",
        company_name: str = "",
    ):
        if not all([smtp_host, smtp_port, smtp_from_email]):
            raise ValueError("Core SMTP settings (host, port, from_email) are missing.")

        # Type narrowing for mypy
        assert smtp_host is not None
        assert smtp_port is not None
        assert smtp_from_email is not None

        self.email_client = AsyncEmailClient(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_from_email=smtp_from_email,
            smtp_use_tls=smtp_use_tls,
        )
        self.renderer = TemplateRenderer(templates_dir)
        self.site_url = site_url
        self.logo_url = logo_url
        self.address = address
        self.company_name = company_name

        self.url_path_confirm = url_path_confirm
        self.url_path_cancel = url_path_cancel
        self.url_path_reschedule = url_path_reschedule
        self.url_path_contact_form = url_path_contact_form

    def _generate_google_calendar_url(self, data: dict) -> str:
        """Генерирует ссылку для добавления события в Google Calendar.

        Ожидает в data:
        - service_name (str) — название события
        - date (str) — дата в формате DD.MM.YYYY
        - time (str) — время в формате HH:MM
        - duration_minutes (int, optional) — длительность в минутах, по умолчанию 60
        """
        try:
            service_name = data.get("service_name", "Appointment")
            date_str = data.get("date")  # DD.MM.YYYY
            time_str = data.get("time")  # HH:MM
            duration = int(data.get("duration_minutes", 60))

            if not date_str or not time_str:
                return ""

            # Парсим начало
            start_dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
            end_dt = start_dt + timedelta(minutes=duration)

            # Формат для Google: YYYYMMDDTHHMMSS (локальное время)
            fmt = "%Y%m%dT%H%M%S"
            dates = f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}"

            base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
            params = {
                "text": service_name,
                "dates": dates,
                "details": f"Your appointment. More info: {self.site_url}",
                "location": self.address,
                "sf": "true",
                "output": "xml",
            }

            query_str = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
            return f"{base_url}&{query_str}"
        except Exception:
            return ""

    def _enrich_context(self, data: dict) -> dict:
        """Обогащает контекст для шаблона письма.

        Добавляет:
        - site_url, logo_url
        - contact_form_url, calendar_url
        - greeting (на основе visits_count если передан)
        - link_confirm, link_cancel, link_reschedule, link_calendar
        """
        context = data.copy()
        clean_site_url = self.site_url.rstrip("/")
        context["site_url"] = clean_site_url
        context["company_name"] = self.company_name

        if self.logo_url:
            if self.logo_url.startswith("http"):
                context["logo_url"] = self.logo_url
            else:
                path = self.logo_url if self.logo_url.startswith("/") else f"/{self.logo_url}"
                context["logo_url"] = f"{clean_site_url}{path}"
        else:
            context["logo_url"] = f"{clean_site_url}/static/img/logo.png"

        if self.url_path_contact_form:
            path = (
                self.url_path_contact_form
                if self.url_path_contact_form.startswith("/")
                else f"/{self.url_path_contact_form}"
            )
            context["contact_form_url"] = f"{clean_site_url}{path}"
        else:
            context["contact_form_url"] = "#"

        # Генерируем ссылку на Google Calendar
        context["calendar_url"] = self._generate_google_calendar_url(data)

        # Приветствие на основе количества визитов (опционально).
        # TODO: Адаптируй логику приветствия под свой проект или убери если не нужно.
        if "name" in context and "greeting" not in context:
            visits = int(context.get("visits_count", 0))
            name = context["name"]
            if visits == 0:
                context["greeting"] = f"Dear {name},"
            elif 1 <= visits <= 4:
                context["greeting"] = f"Hello {name},"
            else:
                context["greeting"] = f"Hi {name},"

        action_token = data.get("action_token")
        if self.url_path_confirm and action_token:
            context["link_confirm"] = f"{clean_site_url}{self.url_path_confirm.format(token=action_token)}"
        else:
            context["link_confirm"] = "#"

        if self.url_path_cancel and action_token:
            context["link_cancel"] = f"{clean_site_url}{self.url_path_cancel.format(token=action_token)}"
        else:
            context["link_cancel"] = "#"

        if self.url_path_reschedule:
            path = (
                self.url_path_reschedule if self.url_path_reschedule.startswith("/") else f"/{self.url_path_reschedule}"
            )
            context["link_reschedule"] = f"{clean_site_url}{path}"
            context["link_calendar"] = f"{clean_site_url}{path}"
        else:
            context["link_reschedule"] = "#"
            context["link_calendar"] = "#"

        return context

    async def send_notification(self, email: str, subject: str, template_name: str, data: dict):
        """Рендерит шаблон и отправляет письмо."""
        full_context = self._enrich_context(data)
        html_content = self.renderer.render(template_name, full_context)
        await self.email_client.send_email(email, subject, html_content)
