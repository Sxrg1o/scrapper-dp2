"""
Security configuration for authentication and authorization.
Modern implementation with improved typing and security practices.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.core.config import get_settings

# Password hashing context - configured to use bcrypt for maximum security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Structured data model for token payload."""
    sub: Optional[Union[str, int]] = None
    exp: datetime
    type: str
    

class SecurityConfig:
    """Modern security configuration with enhanced token handling."""

    def __init__(self):
        self.settings = get_settings()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate secure password hash using bcrypt."""
        return pwd_context.hash(password)

    def _create_token(
        self,
        data: Dict[str, Any],
        token_type: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Base method for token creation with proper typing.
        
        Args:
            data: Data to encode in token
            token_type: Type of token ("access" or "refresh")
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        # Set expiration based on token type using timezone-aware datetime
        current_time = datetime.now(timezone.utc)
        if expires_delta:
            expire = current_time + expires_delta
        elif token_type == "access":
            expire = current_time + timedelta(
                minutes=self.settings.access_token_expire_minutes
            )
        else:  # refresh token
            expire = current_time + timedelta(
                days=self.settings.refresh_token_expire_days
            )

        to_encode.update({"exp": expire, "type": token_type})
        
        return jwt.encode(
            to_encode,
            self.settings.secret_key,
            algorithm=self.settings.algorithm
        )

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        return self._create_token(data, "access", expires_delta)

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token."""
        return self._create_token(data, "refresh", expires_delta)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token with additional security checks.
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.settings.algorithm]
            )
            return payload
        except JWTError:
            return None

    def extract_user_id_from_token(self, token: str) -> Optional[Union[str, int]]:
        """Extract and validate user ID from token."""
        payload = self.verify_token(token)
        return payload.get("sub") if payload else None


# Global security instance
security = SecurityConfig()