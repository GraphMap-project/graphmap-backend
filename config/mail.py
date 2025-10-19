import os

from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig

load_dotenv()

EMAIL_CONFIG = ConnectionConfig(
    MAIL_USERNAME=os.getenv("SENDER_EMAIL"),  # Replace with your email
    MAIL_PASSWORD=os.getenv("SENDER_PASSWORD"),  # Replace with your app password
    MAIL_FROM=os.getenv("SENDER_EMAIL"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

FRONTEND_URL = os.getenv("DOMEN")
