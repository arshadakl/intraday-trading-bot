"""Authentication Module - OTP via Email + JWT Tokens"""

import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Tuple
import jwt
from flask import request, jsonify
from loguru import logger


# ==================== Configuration ====================

def get_auth_config():
    """Get authentication configuration from environment"""
    return {
        'smtp_email': os.environ.get('AUTH_SMTP_EMAIL', ''),
        'smtp_password': os.environ.get('AUTH_SMTP_APP_PASSWORD', ''),
        'user_email': os.environ.get('AUTH_USER_EMAIL', ''),
        'smtp_host': os.environ.get('AUTH_SMTP_HOST', 'smtp.gmail.com'),
        'smtp_port': int(os.environ.get('AUTH_SMTP_PORT', '465')),
        'smtp_use_ssl': os.environ.get('AUTH_SMTP_USE_SSL', 'true').lower() in ('1', 'true', 'yes'),
        'smtp_use_tls': os.environ.get('AUTH_SMTP_USE_TLS', 'false').lower() in ('1', 'true', 'yes'),
        'smtp_timeout': float(os.environ.get('AUTH_SMTP_TIMEOUT', '10')),
        'jwt_secret': os.environ.get('AUTH_JWT_SECRET', 'default-secret-change-me'),
        'token_validity_days': int(os.environ.get('AUTH_TOKEN_VALIDITY_DAYS', '7'))
    }


# ==================== OTP Storage ====================

# In-memory OTP storage (simple for single-user system)
# Format: {'otp': '12345678', 'created_at': datetime, 'attempts': 0}
_current_otp = None


def generate_otp() -> str:
    """Generate an 8-digit OTP code"""
    return ''.join(random.choices(string.digits, k=8))


def store_otp(otp: str) -> None:
    """Store OTP with timestamp"""
    from src.utils.timezone import now_ist
    global _current_otp
    _current_otp = {
        'otp': otp,
        'created_at': now_ist(),
        'attempts': 0
    }
    logger.info(f"🔐 OTP generated and stored")


def verify_otp(code: str) -> Tuple[bool, str]:
    """
    Verify OTP code.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    global _current_otp
    
    if _current_otp is None:
        return False, "No OTP requested. Please request a new code."
    
    # Check expiry (10 minutes)
    from src.utils.timezone import now_ist
    elapsed = now_ist() - _current_otp['created_at']
    if elapsed > timedelta(minutes=10):
        _current_otp = None
        return False, "OTP expired. Please request a new code."
    
    # Check attempts (max 5)
    if _current_otp['attempts'] >= 5:
        _current_otp = None
        return False, "Too many attempts. Please request a new code."
    
    _current_otp['attempts'] += 1
    
    # Verify code
    if code == _current_otp['otp']:
        _current_otp = None  # Clear after successful verification
        logger.success("✅ OTP verified successfully")
        return True, "OTP verified successfully"
    
    remaining = 5 - _current_otp['attempts']
    return False, f"Invalid OTP. {remaining} attempts remaining."


# ==================== Email Sending ====================

def send_otp_email(otp: str) -> Tuple[bool, str]:
    """
    Send OTP to user's email via Gmail SMTP.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    config = get_auth_config()
    
    if not config['smtp_email'] or not config['smtp_password']:
        logger.error("❌ SMTP credentials not configured")
        return False, "Email service not configured"
    
    if not config['user_email']:
        logger.error("❌ User email not configured")
        return False, "User email not configured"
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🔐 Trading Bot Auth Code: {otp}'
        msg['From'] = config['smtp_email']
        msg['To'] = config['user_email']
        
        # HTML email body
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #1a1a2e;">
            <div style="max-width: 400px; margin: 0 auto; background: #16213e; border-radius: 10px; padding: 30px; color: #eee;">
                <h2 style="color: #4ade80; text-align: center;">📊 Trading Bot</h2>
                <p style="text-align: center; color: #aaa;">Your authentication code is:</p>
                <div style="background: #0f3460; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #4ade80;">{otp}</span>
                </div>
                <p style="text-align: center; color: #888; font-size: 12px;">
                    This code expires in 10 minutes.<br>
                    If you didn't request this, ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text = f"Your Trading Bot authentication code is: {otp}\n\nThis code expires in 10 minutes."
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        # Send via configurable SMTP server
        smtp_host = config.get('smtp_host', 'smtp.gmail.com')
        smtp_port = config.get('smtp_port', 465)
        use_ssl = config.get('smtp_use_ssl', True)
        use_tls = config.get('smtp_use_tls', False)
        timeout = config.get('smtp_timeout', 10)

        if use_ssl:
            # Implicit SSL (recommended for port 465)
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout) as server:
                server.login(config['smtp_email'], config['smtp_password'])
                server.send_message(msg)
        else:
            # Plain connection with optional STARTTLS (commonly port 587)
            with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(config['smtp_email'], config['smtp_password'])
                server.send_message(msg)

        logger.success(f"📧 OTP email sent to {config['user_email'][:3]}***")
        return True, "Code sent to your email"
        
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ SMTP authentication failed - check app password")
        return False, "Email authentication failed"
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, OSError) as e:
        logger.error(f"❌ Email sending connection error: {e}")
        return False, "Email connection failed"
    except Exception as e:
        logger.error(f"❌ Email sending error: {e}")
        return False, "Failed to send email"


# ==================== JWT Tokens ====================

def create_jwt_token() -> str:
    """Create a JWT token with configured validity"""
    config = get_auth_config()
    
    payload = {
        'email': config['user_email'],
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=config['token_validity_days'])
    }
    
    token = jwt.encode(payload, config['jwt_secret'], algorithm='HS256')
    logger.info(f"🔑 JWT token created (valid for {config['token_validity_days']} days)")
    return token


def verify_jwt_token(token: str) -> Tuple[bool, Optional[dict], str]:
    """
    Verify a JWT token.
    
    Returns:
        Tuple of (valid: bool, payload: dict or None, message: str)
    """
    config = get_auth_config()
    
    try:
        payload = jwt.decode(token, config['jwt_secret'], algorithms=['HS256'])
        return True, payload, "Token valid"
    except jwt.ExpiredSignatureError:
        return False, None, "Token expired"
    except jwt.InvalidTokenError as e:
        return False, None, f"Invalid token: {str(e)}"


# ==================== Flask Middleware ====================

def require_auth(f):
    """
    Decorator to require authentication for Flask routes.
    
    Usage:
        @app.route('/api/protected')
        @require_auth
        def protected_route():
            return jsonify({'data': 'secret'})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        valid, payload, message = verify_jwt_token(token)
        
        if not valid:
            return jsonify({
                'success': False,
                'error': message,
                'code': 'AUTH_INVALID'
            }), 401
        
        # Store user info in request context
        request.user = payload
        
        return f(*args, **kwargs)
    
    return decorated


# ==================== Auth Endpoints (to be added to server.py) ====================

def request_auth_code() -> Tuple[dict, int]:
    """
    Handle POST /api/auth/request-code
    Generates OTP and sends to configured email.
    """
    try:
        otp = generate_otp()
        store_otp(otp)
        
        success, message = send_otp_email(otp)
        
        if success:
            return {
                'success': True,
                'message': message,
                'expires_in': 600  # 10 minutes in seconds
            }, 200
        else:
            return {
                'success': False,
                'error': message
            }, 500
            
    except Exception as e:
        logger.error(f"❌ Auth code request error: {e}")
        return {
            'success': False,
            'error': 'Failed to send auth code'
        }, 500


def verify_auth_code(code: str) -> Tuple[dict, int]:
    """
    Handle POST /api/auth/verify-code
    Verifies OTP and returns JWT token.
    """
    if not code:
        return {
            'success': False,
            'error': 'Code is required'
        }, 400
    
    valid, message = verify_otp(code)
    
    if valid:
        token = create_jwt_token()
        config = get_auth_config()
        
        return {
            'success': True,
            'message': 'Authentication successful',
            'token': token,
            'expires_in': config['token_validity_days'] * 24 * 60 * 60  # seconds
        }, 200
    else:
        return {
            'success': False,
            'error': message
        }, 401
