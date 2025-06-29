import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.db import get_connection
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

# Email configuration
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Twilio configuration
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")

def send_alert_notification(message):
    # Fetch all admin emails and phone numbers
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT email, phone_number FROM users WHERE role = 'admin'")
    admins = cursor.fetchall()
    cursor.close()
    conn.close()

    # Send email to each admin
    for admin in admins:
        try:
            send_email(admin["email"], message)
            print(f"✅ Email sent to {admin['email']}")
        except Exception as e:
            print(f"❌ Failed to send email to {admin['email']}: {e}")

    # Send SMS to each admin
    for admin in admins:
        phone = admin.get("phone_number")
        if phone:
            if not phone.startswith("+"):
                phone = "+91" + phone  # Assuming Indian numbers
            try:
                send_sms(phone, message)
                print(f"✅ SMS sent to {phone}")
            except Exception as e:
                print(f"❌ Failed to send SMS to {phone}: {e}")

def send_email(to_email, message):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "🔔 Supply Chain Alert - PirateCart"

    msg.attach(MIMEText(message, "plain"))

    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, to_email, msg.as_string())
    server.quit()

def send_sms(to_number, message):
    client = Client(TWILIO_SID, TWILIO_AUTH)
    client.messages.create(
        body=message,
        from_=TWILIO_PHONE,
        to=to_number
    )
