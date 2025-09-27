# Auth0 Production Tenant Setup Specification

## 1. Overview

This document provides comprehensive guidance for setting up a production Auth0 tenant for the NextGen Fusion Commercial Solar Platform. The setup includes OIDC authentication, SSO/SAML for enterprise users, MFA, and integration with the existing React frontend and FastAPI microservices architecture.

## 2. Auth0 Tenant Creation

### 2.1 Tenant Setup
1. **Create Production Tenant**
   - Navigate to Auth0 Dashboard
   - Create new tenant with production-grade naming: `nextgen-fusion-prod`
   - Select appropriate region (US/EU/AU based on data residency requirements)
   - Configure tenant settings for production environment

2. **Tenant Configuration**
   - Enable custom domains for branding
   - Configure tenant-level security settings
   - Set up logging and monitoring
   - Configure session management and token lifetimes

### 2.2 Domain Configuration
1. **Custom Domain Setup**
   - Configure custom domain: `auth.nextgenfusion.com`
   - Set up SSL certificates
   - Configure DNS records
   - Verify domain ownership

2. **Branding Configuration**
   - Upload company logo and branding assets
   - Customize login/signup pages
   - Configure email templates
   - Set up custom error pages

## 3. Application Registration

### 3.1 React Frontend Application
```json
{
  "name": "NextGen Fusion Frontend",
  "type": "Single Page Application",
  "callbacks": [
    "https://app.nextgenfusion.com/callback",
    "https://staging.nextgenfusion.com/callback"
  ],
  "logout_urls": [
    "https://app.nextgenfusion.com",
    "https://staging.nextgenfusion.com"
  ],
  "web_origins": [
    "https://app.nextgenfusion.com",
    "https://staging.nextgenfusion.com"
  ],
  "grant_types": ["authorization_code", "refresh_token"],
  "token_endpoint_auth_method": "none"
}
```

### 3.2 API Gateway Application
```json
{
  "name": "NextGen Fusion API Gateway",
  "type": "Machine to Machine",
  "identifier": "https://api.nextgenfusion.com",
  "scopes": [
    "read:projects",
    "write:projects",
    "read:designs",
    "write:designs",
    "read:compliance",
    "write:compliance",
    "read:finance",
    "write:finance",
    "admin:users",
    "admin:system"
  ]
}
```

### 3.3 Microservices APIs
Register each microservice as a separate API:
- **Design Service API**: `https://api.nextgenfusion.com/design`
- **Project Service API**: `https://api.nextgenfusion.com/project`
- **Compliance Service API**: `https://api.nextgenfusion.com/compliance`
- **Finance Service API**: `https://api.nextgenfusion.com/finance`
- **Currency Service API**: `https://api.nextgenfusion.com/currency`

## 4. Security Configuration

### 4.1 Multi-Factor Authentication (MFA)
1. **MFA Policy Setup**
   - Enable MFA for all users
   - Configure MFA factors: SMS, Email, TOTP, Push notifications
   - Set up conditional MFA based on risk assessment
   - Configure MFA bypass for trusted devices

2. **MFA Rules Configuration**
```javascript
function (user, context, callback) {
  if (context.protocol === 'oauth2-resource-owner') {
    return callback(null, user, context);
  }
  
  const requireMFA = context.request.geoip.country_code !== 'ZA' ||
                     context.authentication.methods.find(method => method.name === 'mfa') === undefined;
  
  if (requireMFA) {
    context.multifactor = {
      provider: 'any',
      allowRememberBrowser: false
    };
  }
  
  callback(null, user, context);
}
```

### 4.2 SSO/SAML for Enterprise
1. **Enterprise Connections**
   - Configure SAML 2.0 connections for enterprise clients
   - Set up Azure AD, Google Workspace, Okta integrations
   - Configure attribute mapping
   - Set up Just-in-Time (JIT) provisioning

2. **SAML Configuration Template**
```xml
<saml:Assertion>
  <saml:AttributeStatement>
    <saml:Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress">
      <saml:AttributeValue>{user.email}</saml:AttributeValue>
    </saml:Attribute>
    <saml:Attribute Name="http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name">
      <saml:AttributeValue>{user.name}</saml:AttributeValue>
    </saml:Attribute>
    <saml:Attribute Name="role">
      <saml:AttributeValue>{user.app_metadata.role}</saml:AttributeValue>
    </saml:Attribute>
  </saml:AttributeStatement>
</saml:Assertion>
```

## 5. Role-Based Access Control (RBAC)

### 5.1 Roles Definition
| Role | Description | Permissions |
|------|-------------|-------------|
| System Admin | Full system access | admin:system, admin:users, read:*, write:* |
| Project Manager | Project and design management | read:projects, write:projects, read:designs, write:designs |
| Designer | Solar system design | read:designs, write:designs, read:projects |
| Compliance Officer | Compliance and regulatory | read:compliance, write:compliance, read:projects |
| Finance Manager | Financial operations | read:finance, write:finance, read:projects |
| Viewer | Read-only access | read:projects, read:designs |

### 5.2 Permission Scopes
```json
{
  "scopes": {
    "read:projects": "Read project information",
    "write:projects": "Create and modify projects",
    "read:designs": "Read solar design data",
    "write:designs": "Create and modify designs",
    "read:compliance": "Read compliance data",
    "write:compliance": "Manage compliance requirements",
    "read:finance": "Read financial data",
    "write:finance": "Manage financial operations",
    "admin:users": "Manage user accounts",
    "admin:system": "System administration"
  }
}
```

### 5.3 Rules for Role Assignment
```javascript
function (user, context, callback) {
  const namespace = 'https://nextgenfusion.com/';
  
  // Default role assignment based on email domain
  if (user.email.endsWith('@nextgenfusion.com')) {
    user.app_metadata = user.app_metadata || {};
    user.app_metadata.role = user.app_metadata.role || 'project_manager';
  } else {
    user.app_metadata = user.app_metadata || {};
    user.app_metadata.role = user.app_metadata.role || 'viewer';
  }
  
  // Add role to token
  context.idToken[namespace + 'role'] = user.app_metadata.role;
  context.accessToken[namespace + 'role'] = user.app_metadata.role;
  
  auth0.users.updateAppMetadata(user.user_id, user.app_metadata)
    .then(() => callback(null, user, context))
    .catch(err => callback(err));
}
```

## 6. Environment Configuration

### 6.1 Production Environment Variables
```bash
# Auth0 Configuration
VITE_AUTH0_DOMAIN=nextgen-fusion-prod.auth0.com
VITE_AUTH0_CLIENT_ID=<production_client_id>
VITE_AUTH0_AUDIENCE=https://api.nextgenfusion.com
VITE_AUTH0_REDIRECT_URI=https://app.nextgenfusion.com/callback
VITE_AUTH0_LOGOUT_URI=https://app.nextgenfusion.com

# Backend Auth0 Configuration
AUTH0_DOMAIN=nextgen-fusion-prod.auth0.com
AUTH0_API_AUDIENCE=https://api.nextgenfusion.com
AUTH0_CLIENT_ID=<backend_client_id>
AUTH0_CLIENT_SECRET=<backend_client_secret>

# Security Settings
AUTH0_MFA_ENABLED=true
AUTH0_SSO_ENABLED=true
AUTH0_SESSION_TIMEOUT=3600
AUTH0_TOKEN_LIFETIME=86400
```

### 6.2 Staging Environment Variables
```bash
# Auth0 Configuration
VITE_AUTH0_DOMAIN=nextgen-fusion-staging.auth0.com
VITE_AUTH0_CLIENT_ID=<staging_client_id>
VITE_AUTH0_AUDIENCE=https://staging-api.nextgenfusion.com
VITE_AUTH0_REDIRECT_URI=https://staging.nextgenfusion.com/callback
VITE_AUTH0_LOGOUT_URI=https://staging.nextgenfusion.com
```

## 7. API Integration

### 7.1 JWT Token Validation
```python
# FastAPI JWT validation middleware
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
import jwt
import requests

security = HTTPBearer()

def verify_token(token: str = Depends(security)):
    try:
        # Get Auth0 public key
        jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
        jwks = requests.get(jwks_url).json()
        
        # Decode and verify token
        payload = jwt.decode(
            token.credentials,
            jwks,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )
        
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 7.2 Microservices Authentication
```typescript
// API Gateway Auth0 middleware
import { auth } from 'express-oauth-server';
import jwt from 'jsonwebtoken';
import jwksClient from 'jwks-rsa';

const client = jwksClient({
  jwksUri: `https://${process.env.AUTH0_DOMAIN}/.well-known/jwks.json`
});

export const authenticateToken = async (req, res, next) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) throw new Error('No token provided');
    
    const decoded = jwt.decode(token, { complete: true });
    const key = await client.getSigningKey(decoded.header.kid);
    
    const verified = jwt.verify(token, key.getPublicKey(), {
      audience: process.env.AUTH0_AUDIENCE,
      issuer: `https://${process.env.AUTH0_DOMAIN}/`,
      algorithms: ['RS256']
    });
    
    req.user = verified;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Unauthorized' });
  }
};
```

## 8. Testing and Validation

### 8.1 Authentication Flow Testing
1. **Login Flow Validation**
   - Test standard email/password login
   - Verify MFA enforcement
   - Test SSO/SAML integration
   - Validate token generation and refresh

2. **Authorization Testing**
   - Test role-based access control
   - Verify API endpoint permissions
   - Test cross-service authentication
   - Validate token expiration handling

### 8.2 Security Testing
```javascript
// Jest test for token validation
describe('Auth0 Integration', () => {
  test('should validate valid JWT token', async () => {
    const token = await getValidToken();
    const result = await validateToken(token);
    expect(result.sub).toBeDefined();
    expect(result.aud).toBe(process.env.AUTH0_AUDIENCE);
  });
  
  test('should reject invalid token', async () => {
    const invalidToken = 'invalid.token.here';
    await expect(validateToken(invalidToken)).rejects.toThrow();
  });
  
  test('should enforce MFA for sensitive operations', async () => {
    const user = await loginUser('test@example.com', 'password');
    expect(user.multifactor_required).toBe(true);
  });
});
```

## 9. Migration Checklist

### 9.1 Pre-Migration Tasks
- [ ] Create production Auth0 tenant
- [ ] Configure custom domain and SSL
- [ ] Set up enterprise connections (SAML/SSO)
- [ ] Configure MFA policies
- [ ] Create and test all applications
- [ ] Set up RBAC roles and permissions
- [ ] Configure production environment variables
- [ ] Test authentication flows in staging

### 9.2 Migration Execution
- [ ] Update DNS records for custom domain
- [ ] Deploy updated environment variables
- [ ] Update application configurations
- [ ] Migrate user data (if applicable)
- [ ] Test all authentication flows
- [ ] Verify API integrations
- [ ] Monitor logs and metrics

### 9.3 Post-Migration Validation
- [ ] Verify all login methods work
- [ ] Test MFA enforcement
- [ ] Validate SSO/SAML connections
- [ ] Check API authentication
- [ ] Monitor error rates and performance
- [ ] Validate user role assignments
- [ ] Test token refresh mechanisms

## 10. Monitoring and Maintenance

### 10.1 Logging Configuration
```json
{
  "log_streams": [
    {
      "name": "CloudWatch Logs",
      "type": "eventbridge",
      "filters": [
        {
          "type": "category",
          "name": "auth.login.fail"
        },
        {
          "type": "category",
          "name": "auth.signup.fail"
        }
      ]
    }
  ]
}
```

### 10.2 Monitoring Metrics
- Authentication success/failure rates
- MFA completion rates
- Token refresh frequency
- API endpoint access patterns
- User session duration
- Geographic access patterns

### 10.3 Maintenance Tasks
- Regular security updates
- Token lifetime optimization
- User access reviews
- Connection health monitoring
- Performance optimization
- Compliance audits

## 11. Security Compliance

### 11.1 Data Protection
- Implement data encryption at rest and in transit
- Configure data residency based on regional requirements
- Set up data retention policies
- Implement audit logging

### 11.2 Compliance Standards
- SOC 2 Type II compliance
- GDPR compliance for EU users
- ISO 27001 security standards
- Regular penetration testing
- Vulnerability assessments

## 12. Troubleshooting Guide

### 12.1 Common Issues
1. **Token Validation Failures**
   - Check audience and issuer configuration
   - Verify JWKS endpoint accessibility
   - Validate token expiration times

2. **MFA Issues**
   - Check MFA provider configuration
   - Verify user enrollment status
   - Test backup authentication methods

3. **SSO/SAML Problems**
   - Validate SAML metadata
   - Check attribute mapping
   - Verify certificate validity

### 12.2 Support Contacts
- **Auth0 Support**: Enterprise support plan
- **Internal Team**: DevOps and Security teams
- **Documentation**: Auth0 documentation and community forums

This specification provides a comprehensive guide for setting up a production-ready Auth0 tenant that meets the security and scalability requirements of the NextGen Fusion Commercial Solar Platform.