"""JWT encoding and decoding utility in pure Python (no third-party library dependencies)."""
import os
import base64
import hmac
import hashlib
import json
import time
from typing import Optional

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "7d8f49b10cbe4e6a8dc5b1285223a5cf0f82a93b4a2e5d1685b8c9d2f34567ef")

def base64url_encode(data: bytes) -> str:
    """Encode bytes to base64url string."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(data: str) -> bytes:
    """Decode base64url string to bytes."""
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(username: str, expires_in_seconds: int = 3600) -> str:
    """Create a standard HS256 JWT access token for a given user."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": username,
        "exp": int(time.time()) + expires_in_seconds
    }
    
    header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = base64url_encode(json.dumps(payload).encode('utf-8'))
    
    signature_base = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signature_base, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def verify_access_token(token: str) -> Optional[str]:
    """Verify an HS256 JWT access token and return the username (subject) if valid, or None."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        
        # Recompute and compare signature
        signature_base = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_signature = hmac.new(SECRET_KEY.encode('utf-8'), signature_base, hashlib.sha256).digest()
        expected_signature_b64 = base64url_encode(expected_signature)
        
        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            return None
            
        # Parse payload and verify expiration
        payload = json.loads(base64url_decode(payload_b64).decode('utf-8'))
        
        if int(time.time()) > payload.get("exp", 0):
            return None
            
        return payload.get("sub")
    except Exception:
        return None
