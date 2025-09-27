"""JWT authentication middleware and utilities."""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User, UserSession
from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthenticationError(Exception):
    """Custom authentication error."""
    pass


class TokenManager:
    """JWT token management utilities."""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check token type
            if payload.get("type") != token_type:
                raise AuthenticationError(f"Invalid token type. Expected {token_type}")
            
            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                raise AuthenticationError("Token missing expiration")
            
            if datetime.utcnow() > datetime.fromtimestamp(exp):
                raise AuthenticationError("Token has expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.JWTError:
            raise AuthenticationError("Invalid token")
    
    @staticmethod
    def extract_user_id(token: str) -> str:
        """Extract user ID from token."""
        payload = TokenManager.verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Token missing user ID")
        
        return user_id


class PasswordManager:
    """Password hashing and verification utilities."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)


class SessionManager:
    """User session management utilities."""
    
    @staticmethod
    def create_session(
        db: Session,
        user_id: str,
        refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> UserSession:
        """Create a new user session."""
        session = UserSession(
            user_id=user_id,
            refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    @staticmethod
    def get_session_by_token(db: Session, refresh_token: str) -> Optional[UserSession]:
        """Get session by refresh token."""
        return db.query(UserSession).filter(
            UserSession.refresh_token == refresh_token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()
    
    @staticmethod
    def invalidate_session(db: Session, session_id: str) -> bool:
        """Invalidate a user session."""
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        
        if session:
            session.is_active = False
            session.ended_at = datetime.utcnow()
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def invalidate_user_sessions(db: Session, user_id: str, exclude_session_id: Optional[str] = None) -> int:
        """Invalidate all sessions for a user (except optionally one)."""
        query = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        )
        
        if exclude_session_id:
            query = query.filter(UserSession.id != exclude_session_id)
        
        sessions = query.all()
        count = 0
        
        for session in sessions:
            session.is_active = False
            session.ended_at = datetime.utcnow()
            count += 1
        
        db.commit()
        return count
    
    @staticmethod
    def cleanup_expired_sessions(db: Session) -> int:
        """Clean up expired sessions."""
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at <= datetime.utcnow(),
            UserSession.is_active == True
        ).all()
        
        count = 0
        for session in expired_sessions:
            session.is_active = False
            session.ended_at = datetime.utcnow()
            count += 1
        
        db.commit()
        return count


class AuthService:
    """Main authentication service."""
    
    def __init__(self, db: Session):
        self.db = db
        self.token_manager = TokenManager()
        self.password_manager = PasswordManager()
        self.session_manager = SessionManager()
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        if not self.password_manager.verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def create_user_tokens(self, user: User) -> Dict[str, str]:
        """Create access and refresh tokens for user."""
        access_token = self.token_manager.create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role}
        )
        
        refresh_token = self.token_manager.create_refresh_token(
            data={"sub": user.id}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """Refresh access token using refresh token."""
        try:
            # Verify refresh token
            payload = self.token_manager.verify_token(refresh_token, "refresh")
            user_id = payload.get("sub")
            
            if not user_id:
                raise AuthenticationError("Invalid refresh token")
            
            # Check if session exists and is active
            session = self.session_manager.get_session_by_token(self.db, refresh_token)
            if not session:
                raise AuthenticationError("Invalid or expired session")
            
            # Get user
            user = self.db.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise AuthenticationError("User not found or inactive")
            
            # Create new access token
            access_token = self.token_manager.create_access_token(
                data={"sub": user.id, "email": user.email, "role": user.role}
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer"
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Token refresh failed: {str(e)}")
    
    def get_user_from_token(self, token: str) -> Optional[User]:
        """Get user from access token."""
        try:
            user_id = self.token_manager.extract_user_id(token)
            
            user = self.db.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            return user
            
        except AuthenticationError:
            return None
    
    def logout_user(self, refresh_token: str) -> bool:
        """Logout user by invalidating session."""
        session = self.session_manager.get_session_by_token(self.db, refresh_token)
        
        if session:
            return self.session_manager.invalidate_session(self.db, session.id)
        
        return False
    
    async def get_current_user(self, token: str, db: Session):
        """Get current user from JWT token."""
        try:
            # Verify the JWT token
            payload = self.token_manager.verify_token(token)
            
            # Get user from database
            from ..models.user import User
            user = db.query(User).filter(User.id == payload.get("sub")).first()
            
            return user
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            raise AuthenticationError("Invalid token")
    
    def logout_all_sessions(self, user_id: str, current_session_id: Optional[str] = None) -> int:
        """Logout user from all sessions except current one."""
        return self.session_manager.invalidate_user_sessions(
            self.db, user_id, current_session_id
        )


def get_auth_service(db: Session) -> AuthService:
    """Get authentication service instance."""
    return AuthService(db)


# FastAPI dependency functions
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to get current user from JWT token."""
    try:
        token = credentials.credentials
        auth_service = get_auth_service(db)
        user = auth_service.get_user_from_token(token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )