# user_home/utils.py
import random
import string
from django.core.mail import send_mail
from django.conf import settings

def send_otp(email):
    otp = ''.join(random.choices(string.digits, k=6))  # Generate a 6-digit OTP

    # Send OTP via Email
    subject = 'EvoTime_Your OTP Code'
    message = f"This is Your OTP code from EvoTime: {otp}"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list)

    # Return the OTP for session storage
    return otp
