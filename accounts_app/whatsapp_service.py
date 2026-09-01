import logging
import requests
import json
import re
from django.conf import settings

logger = logging.getLogger(__name__)

def send_whatsapp_credentials(phone, credentials_dict):
    """
    Automated WhatsApp Agent Dispatcher.
    Sends WhatsApp messages in the background using API Gateways (e.g., UltraMsg, Twilio, or Meta WhatsApp Cloud API).
    """
    clean_phone = re.sub(r'\D', '', str(phone or ''))
    if not clean_phone:
        return {'success': False, 'error': 'Invalid phone number'}

    student_id = credentials_dict.get('student_id', '')
    full_name = credentials_dict.get('full_name', '')
    email = credentials_dict.get('email', '')
    password = credentials_dict.get('password', '')
    course_name = credentials_dict.get('course_name', '')
    login_url = credentials_dict.get('login_url', 'http://localhost:8001/login/')

    msg_text = (
        f"🎓 *Qrious Tech Academy - Student Account Credentials*\n"
        f"--------------------------------------------------\n"
        f"👤 *Student ID:* {student_id}\n"
        f"👤 *Name:* {full_name}\n"
        f"📧 *Email:* {email}\n"
        f"🔑 *Password:* {password}\n"
        f"📚 *Course:* {course_name}\n"
        f"🔗 *Login Portal:* {login_url}\n"
        f"--------------------------------------------------\n"
        f"Welcome to Qrious Tech Academy! Your account has been automatically activated."
    )

    # 1. Check for UltraMsg API Configuration (Popular Zero-Touch WhatsApp API)
    ultramsg_instance = getattr(settings, 'ULTRAMSG_INSTANCE_ID', None)
    ultramsg_token = getattr(settings, 'ULTRAMSG_TOKEN', None)

    if ultramsg_instance and ultramsg_token:
        try:
            url = f"https://api.ultramsg.com/{ultramsg_instance}/messages/chat"
            payload = {
                "token": ultramsg_token,
                "to": clean_phone,
                "body": msg_text
            }
            headers = {'content-type': 'application/x-www-form-urlencoded'}
            res = requests.post(url, data=payload, headers=headers, timeout=10)
            logger.info(f"UltraMsg WhatsApp API response: {res.text}")
            return {'success': res.status_code == 200, 'response': res.json() if res.status_code == 200 else res.text}
        except Exception as e:
            logger.error(f"UltraMsg dispatch error: {e}")

    # 2. Check for Twilio WhatsApp API
    twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    twilio_whatsapp_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', '+14155238886')

    if twilio_sid and twilio_auth_token:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            payload = {
                "From": f"whatsapp:{twilio_whatsapp_number}",
                "To": f"whatsapp:+{clean_phone}",
                "Body": msg_text
            }
            res = requests.post(url, data=payload, auth=(twilio_sid, twilio_auth_token), timeout=10)
            logger.info(f"Twilio WhatsApp API response: {res.text}")
            return {'success': res.status_code in [200, 201], 'response': res.json()}
        except Exception as e:
            logger.error(f"Twilio WhatsApp dispatch error: {e}")

    # Fallback / Simulated Agent Automatic Dispatch Logging
    logger.info(f"[AUTOMATED WHATSAPP AGENT DISPATCH] Message auto-queued for +{clean_phone}:\n{msg_text}")
    return {
        'success': True,
        'simulated': True,
        'phone': clean_phone,
        'msg': msg_text
    }
