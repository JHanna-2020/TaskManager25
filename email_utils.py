"""
Email utility module for Task Manager
Handles sending email notifications with proper error handling and logging
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()


def send_email(to_email, subject, body):
    """
    Send an email using Gmail SMTP

    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        body (str): Email body content

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASSWORD")  # This should be an App Password

    # Validate credentials
    if not sender_email or not sender_password:
        logging.error("Email credentials missing in .env file")
        print("Error: EMAIL_USER or EMAIL_PASSWORD not found in .env file")
        return False

    logging.info(f"Attempting to send email from {sender_email} to {to_email}")

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Add body to email
        msg.attach(MIMEText(body, 'plain'))

        # Gmail SMTP configuration - Using STARTTLS (port 587)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Enable security
        server.login(sender_email, sender_password)

        # Send email
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()

        logging.info(f"Email successfully sent to {to_email}")
        print(f"Email sent successfully to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"SMTP Authentication Error: {e}")
        print("Authentication failed. Make sure you're using an App Password (not your regular Gmail password)")
        print(
            "Enable 2-Factor Authentication and generate an App Password at: https://myaccount.google.com/apppasswords")
        return False

    except smtplib.SMTPRecipientsRefused as e:
        logging.error(f"Recipients refused: {e}")
        print(f"Email address {to_email} was refused by the server")
        return False

    except smtplib.SMTPConnectError as e:
        logging.error(f"SMTP Connection Error: {e}")
        print("Failed to connect to Gmail SMTP server. Check your internet connection.")
        return False

    except Exception as e:
        logging.error(f"Unexpected error sending email: {e}")
        print(f"Failed to send email: {e}")
        return False


def send_email_ssl(to_email, subject, body):
    """
    Alternative email function using SSL (port 465) instead of STARTTLS
    Use this if the main send_email function doesn't work

    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        body (str): Email body content

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        logging.error("Email credentials missing in .env file")
        return False

    try:
        # Create message
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email

        # Gmail SMTP with SSL (port 465)
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        logging.info(f"Email successfully sent to {to_email} (SSL)")
        return True

    except Exception as e:
        logging.error(f"Failed to send email via SSL: {e}")
        return False


def test_email_setup():
    """
    Test the email configuration by sending a test email to yourself

    Returns:
        bool: True if test successful, False otherwise
    """
    sender_email = os.getenv("EMAIL_USER")

    if not sender_email:
        print("EMAIL_USER not found in .env file")
        return False

    print("Testing email configuration...")

    # Test sending an email to yourself
    result = send_email(
        sender_email,
        "Task Manager Email Test",
        "This is a test email from your Task Manager application. If you receive this, your email setup is working!"
    )

    if result:
        print("✅ Email test successful!")
    else:
        print("❌ Email test failed. Trying SSL method...")
        # Try SSL method as fallback
        result = send_email_ssl(
            sender_email,
            "Task Manager Email Test (SSL)",
            "This is a test email using SSL method. If you receive this, your email setup is working!"
        )
        if result:
            print("✅ Email test successful with SSL method!")
        else:
            print("❌ Both email methods failed. Check your credentials and setup.")

    return result


if __name__ == "__main__":
    # Run email test when script is executed directly
    test_email_setup()