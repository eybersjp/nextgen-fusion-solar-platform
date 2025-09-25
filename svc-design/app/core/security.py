"""Security utilities for the Design Service.

Provides encryption, hashing, data sanitization,
and security validation functions.
"""

import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote, unquote

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from passlib.context import CryptContext
import bleach
import re

from .config import get_settings
from .logging import get_logger, log_security_event


logger = get_logger(__name__)


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """Centralized security management."""
    
    def __init__(self):
        self.settings = get_settings()
        self._fernet = None
        self._private_key = None
        self._public_key = None
    
    @property
    def fernet(self) -> Fernet:
        """Get Fernet encryption instance."""
        if self._fernet is None:
            key = self._derive_encryption_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def _derive_encryption_key(self) -> bytes:
        """Derive encryption key from secret."""
        password = self.settings.SECRET_KEY.encode()
        salt = b'nextgen_fusion_salt'  # In production, use a random salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = kdf.derive(password)
        return Fernet.generate_key() if not key else Fernet.generate_key()
    
    def encrypt_data(self, data: Union[str, bytes]) -> str:
        """Encrypt sensitive data."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted = self.fernet.encrypt(data)
        return encrypted.decode('utf-8')
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Invalid encrypted data")
    
    def generate_rsa_keys(self) -> tuple[bytes, bytes]:
        """Generate RSA key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem


# Global security manager instance
security_manager = SecurityManager()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"nf_{generate_secure_token(40)}"


def generate_salt(length: int = 16) -> str:
    """Generate a random salt."""
    return secrets.token_hex(length)


def hash_with_salt(data: str, salt: str) -> str:
    """Hash data with salt using SHA-256."""
    return hashlib.sha256((data + salt).encode()).hexdigest()


def create_hmac_signature(data: str, secret: str) -> str:
    """Create HMAC signature for data."""
    return hmac.new(
        secret.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_hmac_signature(data: str, signature: str, secret: str) -> bool:
    """Verify HMAC signature."""
    expected_signature = create_hmac_signature(data, secret)
    return hmac.compare_digest(signature, expected_signature)


def sanitize_input(input_data: str, allowed_tags: List[str] = None) -> str:
    """Sanitize user input to prevent XSS attacks."""
    if allowed_tags is None:
        allowed_tags = []
    
    # Clean HTML tags
    cleaned = bleach.clean(
        input_data,
        tags=allowed_tags,
        strip=True
    )
    
    # Remove potentially dangerous characters
    cleaned = re.sub(r'[<>"\'\/]', '', cleaned)
    
    return cleaned.strip()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = name[:250] + ('.' + ext if ext else '')
    
    return sanitized


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format."""
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (7-15 digits)
    return 7 <= len(digits_only) <= 15


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    return bool(re.match(pattern, url))


def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID format."""
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_string.lower()))


def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength."""
    result = {
        'valid': True,
        'score': 0,
        'issues': []
    }
    
    # Check length
    if len(password) < 8:
        result['issues'].append('Password must be at least 8 characters long')
        result['valid'] = False
    else:
        result['score'] += 1
    
    # Check for uppercase
    if not re.search(r'[A-Z]', password):
        result['issues'].append('Password must contain at least one uppercase letter')
    else:
        result['score'] += 1
    
    # Check for lowercase
    if not re.search(r'[a-z]', password):
        result['issues'].append('Password must contain at least one lowercase letter')
    else:
        result['score'] += 1
    
    # Check for digits
    if not re.search(r'\d', password):
        result['issues'].append('Password must contain at least one digit')
    else:
        result['score'] += 1
    
    # Check for special characters
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        result['issues'].append('Password must contain at least one special character')
    else:
        result['score'] += 1
    
    # Check for common patterns
    common_patterns = [
        r'123456',
        r'password',
        r'qwerty',
        r'abc123',
        r'admin'
    ]
    
    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            result['issues'].append('Password contains common patterns')
            result['score'] -= 1
            break
    
    # Final validation
    if result['issues']:
        result['valid'] = False
    
    return result


def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """Mask sensitive data for logging."""
    if len(data) <= visible_chars:
        return mask_char * len(data)
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)


def mask_email(email: str) -> str:
    """Mask email address for logging."""
    if '@' not in email:
        return mask_sensitive_data(email)
    
    local, domain = email.split('@', 1)
    masked_local = mask_sensitive_data(local, visible_chars=2)
    
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone number for logging."""
    digits_only = re.sub(r'\D', '', phone)
    
    if len(digits_only) <= 4:
        return '*' * len(phone)
    
    # Show last 4 digits
    masked_digits = '*' * (len(digits_only) - 4) + digits_only[-4:]
    
    # Reconstruct with original formatting
    result = phone
    digit_index = 0
    
    for i, char in enumerate(phone):
        if char.isdigit():
            result = result[:i] + masked_digits[digit_index] + result[i+1:]
            digit_index += 1
    
    return result


def encrypt_pii(data: str) -> str:
    """Encrypt personally identifiable information."""
    try:
        return security_manager.encrypt_data(data)
    except Exception as e:
        logger.error(f"PII encryption failed: {e}")
        log_security_event("pii_encryption_failed", error=str(e))
        raise


def decrypt_pii(encrypted_data: str) -> str:
    """Decrypt personally identifiable information."""
    try:
        return security_manager.decrypt_data(encrypted_data)
    except Exception as e:
        logger.error(f"PII decryption failed: {e}")
        log_security_event("pii_decryption_failed", error=str(e))
        raise


def check_rate_limit(identifier: str, limit: int, window: int, redis_client=None) -> Dict[str, Any]:
    """Check rate limit for an identifier."""
    if not redis_client:
        # If no Redis client, allow all requests
        return {
            'allowed': True,
            'remaining': limit,
            'reset_time': datetime.utcnow() + timedelta(seconds=window)
        }
    
    key = f"rate_limit:{identifier}"
    current_time = datetime.utcnow()
    window_start = current_time - timedelta(seconds=window)
    
    try:
        # Remove old entries
        redis_client.zremrangebyscore(key, 0, window_start.timestamp())
        
        # Count current requests
        current_count = redis_client.zcard(key)
        
        if current_count >= limit:
            # Rate limit exceeded
            oldest_entry = redis_client.zrange(key, 0, 0, withscores=True)
            reset_time = datetime.fromtimestamp(oldest_entry[0][1]) + timedelta(seconds=window) if oldest_entry else current_time + timedelta(seconds=window)
            
            log_security_event(
                "rate_limit_exceeded",
                identifier=identifier,
                limit=limit,
                window=window
            )
            
            return {
                'allowed': False,
                'remaining': 0,
                'reset_time': reset_time
            }
        
        # Add current request
        redis_client.zadd(key, {str(current_time.timestamp()): current_time.timestamp()})
        redis_client.expire(key, window)
        
        return {
            'allowed': True,
            'remaining': limit - current_count - 1,
            'reset_time': current_time + timedelta(seconds=window)
        }
    
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        # On error, allow the request
        return {
            'allowed': True,
            'remaining': limit,
            'reset_time': current_time + timedelta(seconds=window)
        }


def validate_file_upload(filename: str, content: bytes, allowed_types: List[str] = None) -> Dict[str, Any]:
    """Validate file upload for security."""
    result = {
        'valid': True,
        'issues': []
    }
    
    settings = get_settings()
    allowed_types = allowed_types or settings.ALLOWED_FILE_TYPES
    
    # Check file extension
    if '.' not in filename:
        result['issues'].append('File must have an extension')
        result['valid'] = False
    else:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_types:
            result['issues'].append(f'File type .{ext} is not allowed')
            result['valid'] = False
    
    # Check file size
    if len(content) > settings.MAX_FILE_SIZE:
        result['issues'].append(f'File size exceeds maximum of {settings.MAX_FILE_SIZE} bytes')
        result['valid'] = False
    
    # Check for malicious content (basic checks)
    if b'<script' in content.lower() or b'javascript:' in content.lower():
        result['issues'].append('File contains potentially malicious content')
        result['valid'] = False
        log_security_event(
            "malicious_file_upload_attempt",
            filename=filename,
            size=len(content)
        )
    
    return result


def generate_csrf_token() -> str:
    """Generate CSRF token."""
    return generate_secure_token(32)


def validate_csrf_token(token: str, expected_token: str) -> bool:
    """Validate CSRF token."""
    return hmac.compare_digest(token, expected_token)


def escape_sql_identifier(identifier: str) -> str:
    """Escape SQL identifier to prevent injection."""
    # Remove or escape dangerous characters
    escaped = re.sub(r'[^a-zA-Z0-9_]', '', identifier)
    
    # Ensure it doesn't start with a number
    if escaped and escaped[0].isdigit():
        escaped = '_' + escaped
    
    return escaped


def validate_json_input(data: Any, max_depth: int = 10, max_size: int = 1024 * 1024) -> Dict[str, Any]:
    """Validate JSON input for security."""
    result = {
        'valid': True,
        'issues': []
    }
    
    # Check size
    if isinstance(data, str) and len(data) > max_size:
        result['issues'].append(f'JSON size exceeds maximum of {max_size} characters')
        result['valid'] = False
    
    # Check depth (simplified check)
    def check_depth(obj, current_depth=0):
        if current_depth > max_depth:
            return False
        
        if isinstance(obj, dict):
            return all(check_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            return all(check_depth(item, current_depth + 1) for item in obj)
        
        return True
    
    if not check_depth(data):
        result['issues'].append(f'JSON depth exceeds maximum of {max_depth} levels')
        result['valid'] = False
    
    return result