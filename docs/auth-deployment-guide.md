# NextGen Fusion Commercial Solar Platform
# Authentication System Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the NextGen Fusion Commercial Solar Platform's Auth0-based authentication system to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Auth0 Configuration](#auth0-configuration)
3. [Environment Variables](#environment-variables)
4. [Database Setup](#database-setup)
5. [Deployment Steps](#deployment-steps)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Security Considerations](#security-considerations)
10. [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Required Accounts and Services

- **Auth0 Account**: Production tenant with appropriate plan
- **Vercel Account**: For frontend and API deployment
- **Database**: PostgreSQL instance (recommended: Supabase, AWS RDS, or similar)
- **Redis Instance**: For session management and caching
- **Email Service**: SendGrid or similar for transactional emails
- **Monitoring**: Sentry for error tracking
- **SSL Certificate**: For custom domain (handled by Vercel)

### Development Tools

- Node.js 18+ and npm/pnpm
- Git for version control
- Vercel CLI for deployment
- PostgreSQL client for database operations

## Auth0 Configuration

### 1. Create Auth0 Tenant

```bash
# Create production tenant
# Tenant name: nextgen-fusion-prod
# Region: Choose based on your primary user base
```

### 2. Configure Application

```javascript
// Application Settings
{
  "name": "NextGen Fusion Commercial - Production",
  "type": "Single Page Application",
  "allowed_callback_urls": [
    "https://nextgen-fusion.com/callback",
    "https://nextgen-fusion.vercel.app/callback"
  ],
  "allowed_logout_urls": [
    "https://nextgen-fusion.com",
    "https://nextgen-fusion.vercel.app"
  ],
  "allowed_web_origins": [
    "https://nextgen-fusion.com",
    "https://nextgen-fusion.vercel.app"
  ],
  "allowed_origins": [
    "https://nextgen-fusion.com",
    "https://nextgen-fusion.vercel.app"
  ]
}
```

### 3. Configure API

```javascript
// API Settings
{
  "name": "NextGen Fusion API",
  "identifier": "https://api.nextgen-fusion.com",
  "signing_alg": "RS256",
  "scopes": [
    "read:users",
    "write:users",
    "delete:users",
    "read:projects",
    "write:projects",
    "delete:projects",
    "read:analytics",
    "write:analytics",
    "read:reports",
    "write:reports",
    "read:settings",
    "write:settings",
    "manage:system"
  ]
}
```

### 4. Setup Roles and Permissions

```bash
# Create roles using Auth0 Management API or Dashboard
curl -X POST https://YOUR_DOMAIN.auth0.com/api/v2/roles \
  -H "Authorization: Bearer YOUR_MGMT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Administrator",
    "description": "Full system access"
  }'

# Assign permissions to roles
curl -X POST https://YOUR_DOMAIN.auth0.com/api/v2/roles/ROLE_ID/permissions \
  -H "Authorization: Bearer YOUR_MGMT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "permissions": [
      {"permission_name": "read:users", "resource_server_identifier": "https://api.nextgen-fusion.com"},
      {"permission_name": "write:users", "resource_server_identifier": "https://api.nextgen-fusion.com"}
    ]
  }'
```

### 5. Configure Enterprise Connections (if applicable)

```javascript
// SAML Enterprise Connection
{
  "name": "enterprise-saml",
  "strategy": "samlp",
  "options": {
    "signInEndpoint": "https://customer.idp.com/sso/saml",
    "signOutEndpoint": "https://customer.idp.com/sso/saml/logout",
    "signatureAlgorithm": "rsa-sha256",
    "digestAlgorithm": "sha256",
    "fieldsMap": {
      "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
      "given_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
      "family_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
    }
  }
}
```

## Environment Variables

### Production Environment Variables

Create a `.env.production` file with the following variables:

```bash
# Auth0 Configuration
VITE_AUTH0_DOMAIN=your-tenant.auth0.com
VITE_AUTH0_CLIENT_ID=your_spa_client_id
VITE_AUTH0_AUDIENCE=https://api.nextgen-fusion.com
VITE_AUTH0_REDIRECT_URI=https://nextgen-fusion.com/callback

# Backend Auth0 Configuration
AUTH0_CLIENT_SECRET=your_client_secret
AUTH0_ISSUER_BASE_URL=https://your-tenant.auth0.com
AUTH0_SECRET=your_session_secret_32_chars_min
JWT_SECRET=your_jwt_secret_256_bit

# Database Configuration
DB_HOST=your-db-host.com
DB_PORT=5432
DB_NAME=nextgen_fusion_prod
DB_USER=your_db_user
DB_PASSWORD=your_secure_db_password
DB_SSL=true
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require

# Redis Configuration
REDIS_URL=redis://user:password@host:port

# Email Configuration
SENDGRID_API_KEY=your_sendgrid_api_key
FROM_EMAIL=noreply@nextgen-fusion.com

# Monitoring
SENTRY_DSN=your_sentry_dsn
LOG_LEVEL=info

# Security
ENCRYPTION_KEY=your_32_byte_encryption_key
SESSION_SECRET=your_session_secret
CORS_ORIGIN=https://nextgen-fusion.com,https://nextgen-fusion.vercel.app

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100

# MFA Configuration
MFA_ISSUER=NextGen Fusion Commercial
BACKUP_CODES_COUNT=10

# Token Configuration
TOKEN_EXPIRY_HOURS=24
REFRESH_TOKEN_EXPIRY_DAYS=30
PASSWORD_RESET_EXPIRY_HOURS=2
EMAIL_VERIFICATION_EXPIRY_HOURS=24

# Security Policies
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
AUDIT_LOG_RETENTION_DAYS=90

# File Upload
FILE_UPLOAD_MAX_SIZE=10485760
ALLOWED_FILE_TYPES=image/jpeg,image/png,image/gif,application/pdf,text/csv

# Application
NODE_ENV=production
VITE_APP_NAME=NextGen Fusion Commercial Solar Platform
VITE_APP_VERSION=1.0.0
VITE_API_BASE_URL=https://nextgen-fusion.com/api
```

### Vercel Environment Variables Setup

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Set environment variables
vercel env add AUTH0_DOMAIN production
vercel env add AUTH0_CLIENT_ID production
vercel env add AUTH0_CLIENT_SECRET production
vercel env add AUTH0_AUDIENCE production
vercel env add JWT_SECRET production
vercel env add DATABASE_URL production
vercel env add REDIS_URL production
vercel env add SENDGRID_API_KEY production
vercel env add SENTRY_DSN production
vercel env add ENCRYPTION_KEY production
```

## Database Setup

### 1. Create Production Database

```sql
-- Create database
CREATE DATABASE nextgen_fusion_prod;

-- Create user
CREATE USER nextgen_fusion_user WITH ENCRYPTED PASSWORD 'secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE nextgen_fusion_prod TO nextgen_fusion_user;

-- Connect to database
\c nextgen_fusion_prod;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO nextgen_fusion_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nextgen_fusion_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nextgen_fusion_user;
```

### 2. Run Database Migrations

```bash
# Run the Auth0 migration script
psql -h your-db-host -U nextgen_fusion_user -d nextgen_fusion_prod -f migrations/auth0-migration.sql

# Verify migration
psql -h your-db-host -U nextgen_fusion_user -d nextgen_fusion_prod -c "SELECT * FROM migration_tracking;"
```

### 3. Setup Database Indexes

```sql
-- Performance indexes
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_users_auth0_user_id ON users(auth0_user_id);
CREATE INDEX CONCURRENTLY idx_auth0_user_mapping_email ON auth0_user_mapping(email);
CREATE INDEX CONCURRENTLY idx_auth0_sessions_user_id ON auth0_user_sessions(user_id);
CREATE INDEX CONCURRENTLY idx_auth0_sessions_expires_at ON auth0_user_sessions(expires_at);
CREATE INDEX CONCURRENTLY idx_auth0_audit_logs_timestamp ON auth0_audit_logs(timestamp);
CREATE INDEX CONCURRENTLY idx_auth0_audit_logs_user_id ON auth0_audit_logs(user_id);
```

## Deployment Steps

### 1. Pre-Deployment Checklist

- [ ] Auth0 tenant configured
- [ ] Database migrations tested
- [ ] Environment variables set
- [ ] SSL certificates ready
- [ ] Monitoring tools configured
- [ ] Backup procedures in place
- [ ] Rollback plan prepared

### 2. Deploy to Vercel

```bash
# Clone repository
git clone https://github.com/your-org/nextgen-fusion-commercial.git
cd nextgen-fusion-commercial

# Install dependencies
npm install

# Build and test locally
npm run build
npm run test

# Deploy to Vercel
vercel --prod

# Or deploy with specific configuration
vercel deploy --prod --env-file .env.production
```

### 3. Database Migration in Production

```bash
# Run migration script
node scripts/auth0-migration.js migrate

# Verify migration
node scripts/auth0-migration.js report
```

### 4. Configure Custom Domain

```bash
# Add custom domain in Vercel dashboard
# Configure DNS records:
# CNAME: nextgen-fusion.com -> cname.vercel-dns.com
# A: @ -> 76.76.19.61
```

## Post-Deployment Verification

### 1. Health Checks

```bash
# API health check
curl https://nextgen-fusion.com/api/health

# Auth health check
curl https://nextgen-fusion.com/api/auth/health

# Database connectivity
curl https://nextgen-fusion.com/api/health/database
```

### 2. Authentication Flow Testing

```bash
# Test login endpoint
curl -X POST https://nextgen-fusion.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'

# Test token validation
curl -X POST https://nextgen-fusion.com/api/auth/validate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Frontend Testing

- [ ] Login/logout functionality
- [ ] Role-based access control
- [ ] Enterprise SSO (if configured)
- [ ] MFA enrollment and verification
- [ ] Token refresh mechanism
- [ ] Error handling

### 4. Performance Testing

```bash
# Load testing with Artillery
npm install -g artillery
artillery quick --count 10 --num 5 https://nextgen-fusion.com/api/health

# Monitor response times
curl -w "@curl-format.txt" -o /dev/null -s https://nextgen-fusion.com/api/auth/health
```

## Monitoring and Maintenance

### 1. Application Monitoring

```javascript
// Sentry configuration
import * as Sentry from '@sentry/node'

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: 'production',
  tracesSampleRate: 0.1
})
```

### 2. Database Monitoring

```sql
-- Monitor active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Monitor slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

### 3. Auth0 Monitoring

- Monitor login success/failure rates
- Track MFA enrollment rates
- Monitor API rate limits
- Review security logs

### 4. Automated Maintenance

```bash
# Setup cron jobs for cleanup
# Session cleanup: Daily at 2 AM
0 2 * * * /usr/local/bin/node /app/scripts/cleanup-sessions.js

# Audit log cleanup: Weekly on Sunday at 3 AM
0 3 * * 0 /usr/local/bin/node /app/scripts/cleanup-audit-logs.js

# Token cleanup: Daily at 1 AM
0 1 * * * /usr/local/bin/node /app/scripts/cleanup-tokens.js
```

## Troubleshooting

### Common Issues

#### 1. Auth0 Token Validation Errors

```bash
# Check Auth0 configuration
curl https://YOUR_DOMAIN.auth0.com/.well-known/jwks.json

# Verify JWT token
node -e "console.log(require('jsonwebtoken').decode('YOUR_TOKEN', {complete: true}))"
```

#### 2. Database Connection Issues

```bash
# Test database connection
psql -h your-db-host -U nextgen_fusion_user -d nextgen_fusion_prod -c "SELECT 1;"

# Check connection pool
SELECT * FROM pg_stat_activity WHERE datname = 'nextgen_fusion_prod';
```

#### 3. CORS Issues

```javascript
// Verify CORS configuration
const corsOptions = {
  origin: process.env.CORS_ORIGIN?.split(',') || ['http://localhost:3000'],
  credentials: true,
  optionsSuccessStatus: 200
}
```

#### 4. Rate Limiting Issues

```bash
# Check Redis connection
redis-cli -u $REDIS_URL ping

# Monitor rate limit counters
redis-cli -u $REDIS_URL keys "rate_limit:*"
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=debug
export DEBUG=auth:*

# Run with debug output
node api/app.js
```

## Security Considerations

### 1. Environment Security

- Use strong, unique passwords for all services
- Enable 2FA on all admin accounts
- Regularly rotate secrets and API keys
- Use environment-specific configurations
- Implement proper secret management

### 2. Network Security

- Enable HTTPS everywhere
- Configure proper CORS policies
- Implement rate limiting
- Use security headers
- Monitor for suspicious activity

### 3. Database Security

- Enable SSL connections
- Use connection pooling
- Implement row-level security (RLS)
- Regular security updates
- Backup encryption

### 4. Auth0 Security

- Enable anomaly detection
- Configure attack protection
- Implement proper logout
- Use secure token storage
- Regular security reviews

## Rollback Procedures

### 1. Application Rollback

```bash
# Rollback to previous Vercel deployment
vercel rollback

# Or rollback to specific deployment
vercel rollback DEPLOYMENT_URL
```

### 2. Database Rollback

```sql
-- Rollback Auth0 migration
SELECT rollback_user_migration(user_id) 
FROM auth0_user_mapping 
WHERE migration_status = 'completed';

-- Restore from backup
psql -h your-db-host -U nextgen_fusion_user -d nextgen_fusion_prod < backup.sql
```

### 3. Auth0 Configuration Rollback

- Revert application settings
- Restore previous connection configurations
- Reset role and permission assignments
- Update callback URLs if necessary

### 4. Emergency Procedures

```bash
# Disable authentication temporarily
export BYPASS_AUTH=true

# Enable maintenance mode
export MAINTENANCE_MODE=true

# Redirect traffic to backup
# Update DNS or load balancer configuration
```

## Support and Documentation

### Internal Documentation

- [API Documentation](./api-documentation.md)
- [Frontend Components Guide](./frontend-components.md)
- [Database Schema](./database-schema.md)
- [Security Policies](./security-policies.md)

### External Resources

- [Auth0 Documentation](https://auth0.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)

### Support Contacts

- **Technical Lead**: tech-lead@nextgen-fusion.com
- **DevOps Team**: devops@nextgen-fusion.com
- **Security Team**: security@nextgen-fusion.com
- **Emergency**: emergency@nextgen-fusion.com

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Next Review**: 2024-04-15  
**Owner**: DevOps Team