from background_task import background
from django.core.mail import send_mail
import logging
import io
import openpyxl
from django.db import connection

import io, openpyxl, csv, logging

logger = logging.getLogger(__name__)

@background(schedule=300)  #run after 5 minutes
def check_db_and_mail(recipient, subject="DB Alert"):
    """
    Background task to send an email.
    If email sending fails, log and notify admin.
    The repeat interval is set when scheduling in views.py.
    """
    try:
        send_mail(
            subject=subject,
            message="Your scheduled database report...",
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info(f"✅ Email successfully sent to {recipient}")
    except Exception as e:
        error_msg = f"❌ Failed to send email to {recipient}: {str(e)}"
        logger.error(error_msg)
        # Optionally notify admin
        send_mail(
            subject="Email Sending Failed",
            message=error_msg,
            from_email=None,
            recipient_list=["admin@example.com"],  # replace with real admin
        )




