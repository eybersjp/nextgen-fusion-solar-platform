import React from 'react'
import { useAuth } from '../../hooks/useAuth'

interface RoleGuardProps {
  children: React.ReactNode
  requiredRoles?: string[]
  requiredPermissions?: string[]
  requireAll?: boolean
  fallback?: React.ReactNode
  showFallback?: boolean
}

/**
 * RoleGuard component for role and permission-based access control
 * 
 * @param children - Content to render if user has required access
 * @param requiredRoles - Array of roles required (user needs at least one unless requireAll is true)
 * @param requiredPermissions - Array of permissions required (user needs at least one unless requireAll is true)
 * @param requireAll - If true, user must have ALL specified roles/permissions
 * @param fallback - Component to render when access is denied
 * @param showFallback - Whether to show fallback component or hide entirely
 */
export const RoleGuard: React.FC<RoleGuardProps> = ({
  children,
  requiredRoles = [],
  requiredPermissions = [],
  requireAll = false,
  fallback = null,
  showFallback = false
}) => {
  const { user, hasRole, hasPermission, isAuthenticated } = useAuth()

  // If not authenticated, don't show content
  if (!isAuthenticated || !user) {
    return showFallback ? <>{fallback}</> : null
  }

  // Check roles
  let hasRequiredRoles = true
  if (requiredRoles.length > 0) {
    if (requireAll) {
      hasRequiredRoles = requiredRoles.every(role => hasRole(role))
    } else {
      hasRequiredRoles = requiredRoles.some(role => hasRole(role))
    }
  }

  // Check permissions
  let hasRequiredPermissions = true
  if (requiredPermissions.length > 0) {
    if (requireAll) {
      hasRequiredPermissions = requiredPermissions.every(permission => hasPermission(permission))
    } else {
      hasRequiredPermissions = requiredPermissions.some(permission => hasPermission(permission))
    }
  }

  // Grant access if user has required roles AND permissions
  const hasAccess = hasRequiredRoles && hasRequiredPermissions

  if (hasAccess) {
    return <>{children}</>
  }

  return showFallback ? <>{fallback}</> : null
}

// Convenience components for common role checks
export const AdminOnly: React.FC<{ children: React.ReactNode; fallback?: React.ReactNode }> = ({ children, fallback }) => (
  <RoleGuard requiredRoles={['admin']} fallback={fallback} showFallback={!!fallback}>
    {children}
  </RoleGuard>
)

export const ManagerOnly: React.FC<{ children: React.ReactNode; fallback?: React.ReactNode }> = ({ children, fallback }) => (
  <RoleGuard requiredRoles={['manager', 'admin']} fallback={fallback} showFallback={!!fallback}>
    {children}
  </RoleGuard>
)

export const UserOnly: React.FC<{ children: React.ReactNode; fallback?: React.ReactNode }> = ({ children, fallback }) => (
  <RoleGuard requiredRoles={['user', 'manager', 'admin']} fallback={fallback} showFallback={!!fallback}>
    {children}
  </RoleGuard>
)

// Permission-based guards
export const CanRead: React.FC<{ resource: string; children: React.ReactNode; fallback?: React.ReactNode }> = ({ resource, children, fallback }) => (
  <RoleGuard requiredPermissions={[`read:${resource}`]} fallback={fallback} showFallback={!!fallback}>
    {children}
  </RoleGuard>
)

export const CanWrite: React.FC<{ resource: string; children: React.ReactNode; fallback?: React.ReactNode }> = ({ resource, children, fallback }) => (
  <RoleGuard requiredPermissions={[`write:${resource}`]} fallback={fallback} showFallback={!!fallback}>
    {children}
  </RoleGuard>
)

export const CanDelete: React.FC<{ resource: string; children: React.ReactNode; fallback?: React.ReactNode }> = ({ resource, children, fallback }) => (
  <RoleGuard requiredPermissions={[`delete:${resource}`]} fallback={fallback} showFallback={!!fallback}>
    {children}
  </RoleGuard>
)

export default RoleGuard