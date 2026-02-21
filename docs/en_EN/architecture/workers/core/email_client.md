# 📜 Email Client

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This module defines the `AsyncEmailClient` class, which provides an asynchronous interface for sending HTML emails using SMTP. It leverages `aiosmtplib` for non-blocking email transmission, making it suitable for background worker tasks.

## `AsyncEmailClient` Class

The `AsyncEmailClient` encapsulates the configuration and logic required to connect to an SMTP server and send emails.

### Initialization (`__init__`)

```python
def __init__(
    self,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from_email: str,
    smtp_use_tls: bool,
):
```
Initializes the `AsyncEmailClient` with SMTP server details and authentication credentials.

*   `smtp_host` (`str`): The hostname or IP address of the SMTP server.
*   `smtp_port` (`int`): The port number of the SMTP server.
*   `smtp_user` (`str`): The username for SMTP authentication.
*   `smtp_password` (`str`): The password for SMTP authentication.
*   `smtp_from_email` (`str`): The email address to be used as the sender.
*   `smtp_use_tls` (`bool`): A flag indicating whether to use TLS encryption for the connection.

### `send_email` Method

```python
async def send_email(self, to_email: str, subject: str, html_content: str):
```
Asynchronously sends an HTML email to a specified recipient.

*   `to_email` (`str`): The recipient's email address.
*   `subject` (`str`): The subject line of the email.
*   `html_content` (`str`): The HTML content of the email body.

**Process:**
1.  **Message Construction:** Creates an `EmailMessage` object, setting the sender, recipient, subject, and both plain-text fallback content and the provided HTML content.
2.  **SMTP Transmission:** Uses `aiosmtplib.send()` to connect to the configured SMTP server and send the email.
    *   It explicitly sets `start_tls=False` because `use_tls=True` on port 465 typically implies a direct SSL/TLS connection, not STARTTLS.
3.  **Logging:** Logs the success or failure of the email transmission.
4.  **Error Handling:** Raises any exceptions that occur during the email sending process.
