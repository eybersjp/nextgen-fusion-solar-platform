from typing import Optional, Dict, Any, List
from fastapi import Depends, HTTPException, status
from ..middleware.auth0_middleware import auth0_security, optional_auth0_security


async def get_current_user(user_info: Dict[str, Any] = Depends(auth0_security)) -> Dict[str, Any]:
    """
    Get current authenticated user from Auth0 token
    """
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user_info


async def get_current_user_optional(user_info: Optional[Dict[str, Any]] = Depends(optional_auth0_security)) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, None otherwise
    """
    return user_info


def require_role(role: str):
    """
    Dependency factory to require a specific role
    """
    async def role_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_roles = current_user.get('roles', [])
        if role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {role}"
            )
        return current_user
    return role_dependency


def require_any_role(*roles: str):
    """
    Dependency factory to require any of the specified roles
    """
    async def roles_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_roles = current_user.get('roles', [])
        if not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}"
            )
        return current_user
    return roles_dependency


def require_permission(permission: str):
    """
    Dependency factory to require a specific permission
    """
    async def permission_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_permissions = current_user.get('permissions', [])
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {permission}"
            )
        return current_user
    return permission_dependency


def require_permissions(*permissions: str):
    """
    Dependency factory to require multiple permissions
    """
    async def permissions_dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_permissions = current_user.get('permissions', [])
        missing_permissions = [perm for perm in permissions if perm not in user_permissions]
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing permissions: {', '.join(missing_permissions)}"
            )
        return current_user
    return permissions_dependency


# Role-based dependencies for common roles
require_admin = require_role('Admin')
require_manager = require_role('Manager')
require_engineer = require_role('Engineer')
require_viewer = require_role('Viewer')

# Permission-based dependencies for common permissions
require_read_projects = require_permission('read:projects')
require_write_projects = require_permission('write:projects')
require_delete_projects = require_permission('delete:projects')
require_read_users = require_permission('read:users')
require_write_users = require_permission('write:users')
require_read_compliance = require_permission('read:compliance')
require_write_compliance = require_permission('write:compliance')
require_read_finance = require_permission('read:finance')
require_write_finance = require_permission('write:finance')

# Combined role dependencies
require_admin_or_manager = require_any_role('Admin', 'Manager')
require_staff = require_any_role('Admin', 'Manager', 'Engineer')