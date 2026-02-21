from email.message import EmailMessage
from typing import Any

import aiosmtplib
from loguru import logger


class AsyncEmailClient:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        smtp_from_email: str | None = None,
        smtp_use_tls: bool = False,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.smtp_from_email = smtp_from_email
        self.smtp_use_tls = smtp_use_tls

    async def send_email(self, to_email: str, subject: str, html_content: str, timeout: int = 15):
        """
        Асинхронная отправка HTML-письма.
        """
        message = EmailMessage()
        message["From"] = self.smtp_from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content("Please enable HTML to view this email.")
        message.add_alternative(html_content, subtype="html")

        # Авто-определение режима шифрования
        use_ssl = self.smtp_port == 465
        start_tls = self.smtp_port == 587 or (self.smtp_use_tls and self.smtp_port != 465)

        send_kwargs: dict[str, Any] = {
            "hostname": self.smtp_host,
            "port": self.smtp_port,
            "use_tls": use_ssl,
            "start_tls": start_tls,
            "timeout": timeout,  # Добавляем таймаут для предотвращения зависания
        }

        if self.smtp_user and self.smtp_password:
            send_kwargs["username"] = self.smtp_user
            send_kwargs["password"] = self.smtp_password

        try:
            logger.debug(
                f"Attempting to send email to {to_email} via {self.smtp_host}:{self.smtp_port} (SSL:{use_ssl}, TLS:{start_tls})"
            )
            await aiosmtplib.send(message, **send_kwargs)
            logger.info(f"Email sent successfully to {to_email} via {self.smtp_host}")
        except aiosmtplib.SMTPConnectError:
            logger.error(f"Connection failed to {self.smtp_host}:{self.smtp_port}. Check firewall/ports.")
            raise
        except Exception as e:
            logger.error(f"Failed to send email to {to_email} via {self.smtp_host}: {type(e).__name__}: {e}")
            raise e
