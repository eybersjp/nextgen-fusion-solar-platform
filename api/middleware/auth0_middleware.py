import os
import jwt
import requests
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Auth0Middleware:
    """
    Auth0 JWT validation middleware for FastAPI
    Handles Auth0 token validation, JWKS fetching, and user extraction
    """
    
    def __init__(self):
        self.domain = os.getenv('AUTH0_DOMAIN')
        self.api_audience = os.getenv('AUTH0_API_AUDIENCE')
        self.issuer = os.getenv('AUTH0_ISSUER', f'https://{self.domain}/')
        self.algorithms = ['RS256']
        self.jwks_cache = {}
        self.jwks_cache_expiry = None
        
        if not self.domain or not self.api_audience:
            raise ValueError("AUTH0_DOMAIN and AUTH0_API_AUDIENCE must be set")
    
    @lru_cache(maxsize=10)
    def get_jwks(self) -> Dict[str, Any]:
        """
        Fetch and cache JSON Web Key Set (JWKS) from Auth0
        """
        try:
            # Check cache expiry
            if (self.jwks_cache_expiry and 
                datetime.now() < self.jwks_cache_expiry and 
                self.jwks_cache):
                return self.jwks_cache
            
            jwks_url = f'https://{self.domain}/.well-known/jwks.json'
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            
            jwks = response.json()
            
            # Cache for 1 hour
            self.jwks_cache = jwks
            self.jwks_cache_expiry = datetime.now() + timedelta(hours=1)
            
            return jwks
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to verify token - authentication service unavailable"
            )
    
    def get_rsa_key(self, token_header: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract RSA key from JWKS for token validation
        """
        jwks = self.get_jwks()
        
        for key in jwks.get('keys', []):
            if key.get('kid') == token_header.get('kid'):
                return {
                    'kty': key.get('kty'),
                    'kid': key.get('kid'),
                    'use': key.get('use'),
                    'n': key.get('n'),
                    'e': key.get('e')
                }
        
        return None
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode Auth0 JWT token
        """
        try:
            # Get token header without verification
            unverified_header = jwt.get_unverified_header(token)
            
            # Get RSA key for verification
            rsa_key = self.get_rsa_key(unverified_header)
            
            if not rsa_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token - unable to find appropriate key"
                )
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=self.algorithms,
                audience=self.api_audience,
                issuer=self.issuer
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    def extract_user_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from Auth0 token payload
        """
        return {
            'sub': payload.get('sub'),
            'email': payload.get('email'),
            'email_verified': payload.get('email_verified', False),
            'name': payload.get('name'),
            'picture': payload.get('picture'),
            'roles': payload.get('https://nextgen-solar.com/roles', []),
            'permissions': payload.get('https://nextgen-solar.com/permissions', []),
            'auth_provider': 'auth0',
            'aud': payload.get('aud'),
            'iss': payload.get('iss'),
            'iat': payload.get('iat'),
            'exp': payload.get('exp')
        }


class Auth0Security(HTTPBearer):
    """
    FastAPI security dependency for Auth0 authentication
    """
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.auth0_middleware = Auth0Middleware()
    
    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header required"
                )
            return None
        
        # Verify token
        payload = self.auth0_middleware.verify_token(credentials.credentials)
        
        # Extract user info
        user_info = self.auth0_middleware.extract_user_info(payload)
        
        return user_info


# Global instances
auth0_security = Auth0Security()
optional_auth0_security = Auth0Security(auto_error=False)


def require_auth(user_info: Dict[str, Any] = None):
    """
    Dependency to require authentication
    """
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user_info


def require_roles(*required_roles: str):
    """
    Dependency factory to require specific roles
    """
    def role_checker(user_info: Dict[str, Any] = None):
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_roles = user_info.get('roles', [])
        
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(required_roles)}"
            )
        
        return user_info
    
    return role_checker


def require_permissions(*required_permissions: str):
    """
    Dependency factory to require specific permissions
    """
    def permission_checker(user_info: Dict[str, Any] = None):
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_permissions = user_info.get('permissions', [])
        
        if not all(perm in user_permissions for perm in required_permissions):
            missing_perms = [perm for perm in required_permissions if perm not in user_permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Missing: {', '.join(missing_perms)}"
            )
        
        return user_info
    
    return permission_checker