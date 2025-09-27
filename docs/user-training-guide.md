# NextGen Fusion Commercial Solar Platform
# User Training Guide - Authentication System

## Overview

Welcome to the NextGen Fusion Commercial Solar Platform! This guide will help you understand and use the new authentication system effectively. Our platform now uses Auth0 for secure, enterprise-grade authentication with enhanced security features.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Account Creation](#account-creation)
3. [Logging In](#logging-in)
4. [Multi-Factor Authentication (MFA)](#multi-factor-authentication-mfa)
5. [Enterprise Single Sign-On (SSO)](#enterprise-single-sign-on-sso)
6. [User Roles and Permissions](#user-roles-and-permissions)
7. [Account Management](#account-management)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Frequently Asked Questions](#frequently-asked-questions)

## Getting Started

### What's New?

Our authentication system has been upgraded with the following improvements:

- **Enhanced Security**: Industry-standard Auth0 authentication
- **Single Sign-On (SSO)**: Use your company credentials to log in
- **Multi-Factor Authentication (MFA)**: Additional security layer
- **Role-Based Access**: Customized access based on your role
- **Better User Experience**: Streamlined login and account management

### System Requirements

- **Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile**: iOS 14+, Android 10+
- **Internet Connection**: Stable internet connection required
- **JavaScript**: Must be enabled in your browser

## Account Creation

### New User Registration

1. **Visit the Platform**
   - Go to [https://nextgen-fusion.com](https://nextgen-fusion.com)
   - Click "Sign Up" or "Create Account"

2. **Choose Registration Method**
   - **Email/Password**: Create account with email and password
   - **Social Login**: Use Google, Microsoft, or LinkedIn
   - **Enterprise SSO**: Use your company credentials (if available)

3. **Complete Registration Form**
   ```
   Required Information:
   - Full Name
   - Email Address
   - Company Name
   - Job Title
   - Phone Number (optional)
   - Password (if not using SSO)
   ```

4. **Email Verification**
   - Check your email for verification link
   - Click the link to verify your account
   - Return to the platform to complete setup

5. **Profile Setup**
   - Add profile picture (optional)
   - Set timezone and preferences
   - Complete company information

### Enterprise User Onboarding

If your organization uses enterprise SSO:

1. **Domain Detection**
   - Enter your work email address
   - System automatically detects your organization
   - Redirects to your company's login page

2. **First-Time Setup**
   - Complete organization information
   - Set security preferences
   - Review and accept terms

## Logging In

### Standard Login Process

1. **Access Login Page**
   - Go to [https://nextgen-fusion.com](https://nextgen-fusion.com)
   - Click "Log In" or "Sign In"

2. **Enter Credentials**
   - **Email/Password**: Enter your registered email and password
   - **Social Login**: Click your preferred social provider
   - **Enterprise SSO**: Enter work email for automatic redirection

3. **Multi-Factor Authentication** (if enabled)
   - Enter verification code from your authenticator app
   - Or use SMS/Email verification
   - Or use backup codes if primary method unavailable

4. **Access Dashboard**
   - Successfully logged in users see the main dashboard
   - Access is customized based on your role and permissions

### Login Options

#### Email and Password
- Traditional username/password authentication
- Password requirements: 8+ characters, mixed case, numbers, symbols
- "Remember Me" option for trusted devices

#### Social Login
- **Google**: Use your Google account
- **Microsoft**: Use your Microsoft/Office 365 account
- **LinkedIn**: Use your LinkedIn professional account

#### Enterprise SSO
- **SAML**: Security Assertion Markup Language
- **OIDC**: OpenID Connect
- **Active Directory**: Microsoft Active Directory integration

### Forgot Password

1. **Reset Request**
   - Click "Forgot Password?" on login page
   - Enter your registered email address
   - Click "Send Reset Link"

2. **Check Email**
   - Look for password reset email
   - Check spam/junk folder if not received
   - Reset link expires in 2 hours

3. **Create New Password**
   - Click the reset link in email
   - Enter new password (must meet requirements)
   - Confirm new password
   - Log in with new credentials

## Multi-Factor Authentication (MFA)

### Why Use MFA?

MFA adds an extra layer of security by requiring two forms of verification:
1. Something you know (password)
2. Something you have (phone, authenticator app)

### Setting Up MFA

#### Authenticator App (Recommended)

1. **Download Authenticator App**
   - Google Authenticator (iOS/Android)
   - Microsoft Authenticator (iOS/Android)
   - Authy (iOS/Android/Desktop)

2. **Enable in Platform**
   - Go to Account Settings → Security
   - Click "Enable Multi-Factor Authentication"
   - Select "Authenticator App"

3. **Scan QR Code**
   - Open your authenticator app
   - Scan the QR code displayed
   - Enter the 6-digit code to verify

4. **Save Backup Codes**
   - Download and securely store backup codes
   - Use these if you lose access to your device

#### SMS Verification

1. **Enable SMS MFA**
   - Go to Account Settings → Security
   - Select "SMS Verification"
   - Enter your mobile phone number

2. **Verify Phone Number**
   - Receive verification code via SMS
   - Enter code to confirm setup

3. **Login with SMS**
   - Enter password as usual
   - Receive SMS with 6-digit code
   - Enter code to complete login

#### Email Verification

1. **Enable Email MFA**
   - Go to Account Settings → Security
   - Select "Email Verification"
   - Confirm your email address

2. **Login with Email**
   - Enter password as usual
   - Check email for verification code
   - Enter code to complete login

### Using Backup Codes

- Each backup code can only be used once
- Generate new codes after using several
- Store codes securely (password manager recommended)
- Use when primary MFA method is unavailable

### Managing MFA Devices

1. **View Active Devices**
   - Go to Account Settings → Security → MFA Devices
   - See all registered devices and methods

2. **Remove Device**
   - Click "Remove" next to device
   - Confirm removal
   - Ensure you have alternative access method

3. **Add New Device**
   - Click "Add New Device"
   - Follow setup process for chosen method
   - Verify new device works before removing old ones

## Enterprise Single Sign-On (SSO)

### What is SSO?

SSO allows you to use your company's existing credentials to access the NextGen Fusion platform without creating a separate password.

### Benefits of SSO

- **Convenience**: One set of credentials for all company applications
- **Security**: Centralized access control and monitoring
- **Compliance**: Meets enterprise security requirements
- **Productivity**: Faster access to applications

### Using SSO

#### Automatic Detection

1. **Enter Work Email**
   - Go to login page
   - Enter your work email address
   - System detects your organization

2. **Redirect to Company Login**
   - Automatically redirected to your company's login page
   - Use your normal work credentials
   - Complete any additional authentication (MFA, etc.)

3. **Return to Platform**
   - Successfully authenticated users return to NextGen Fusion
   - Access granted based on company-assigned roles

#### Manual SSO Login

1. **Select Your Organization**
   - Click "Sign in with SSO"
   - Choose your organization from the list
   - Or enter your organization's SSO URL

2. **Complete Authentication**
   - Follow your organization's login process
   - May include username/password, smart card, or biometrics
   - Complete any required MFA steps

### SSO Troubleshooting

#### Common Issues

- **Organization Not Found**: Contact your IT administrator
- **Access Denied**: Check with your manager about platform access
- **Login Loop**: Clear browser cache and cookies
- **Certificate Errors**: Ensure your browser trusts company certificates

#### Getting Help

- **IT Support**: Contact your company's IT helpdesk
- **Platform Support**: Email support@nextgen-fusion.com
- **Manager**: Verify you should have platform access

## User Roles and Permissions

### Understanding Roles

Your role determines what you can see and do in the platform:

#### Administrator
- **Full Access**: All platform features and settings
- **User Management**: Create, edit, and delete user accounts
- **System Settings**: Configure platform-wide settings
- **Analytics**: Access to all reports and analytics
- **Audit Logs**: View security and activity logs

#### Manager
- **Team Management**: Manage team members and projects
- **Reports**: Access to team and project reports
- **Analytics**: View performance metrics and dashboards
- **Project Creation**: Create and configure new projects
- **Budget Management**: View and manage project budgets

#### User
- **Project Access**: View and edit assigned projects
- **Data Entry**: Input and update project data
- **Basic Reports**: Generate standard reports
- **Profile Management**: Update personal profile
- **Notifications**: Receive and manage notifications

#### Viewer
- **Read-Only Access**: View projects and data
- **Basic Reports**: Generate read-only reports
- **Dashboard**: View assigned dashboards
- **Profile**: Update personal information only

### Permission-Based Features

Some features require specific permissions:

#### Financial Data
- **View**: See financial information
- **Edit**: Modify financial data
- **Approve**: Approve financial transactions

#### Project Management
- **Create**: Start new projects
- **Edit**: Modify project details
- **Delete**: Remove projects
- **Archive**: Archive completed projects

#### User Management
- **View Users**: See user list and profiles
- **Edit Users**: Modify user information
- **Manage Roles**: Assign and change user roles
- **Delete Users**: Remove user accounts

#### System Administration
- **System Settings**: Configure platform settings
- **Integration Management**: Manage third-party integrations
- **Security Settings**: Configure security policies
- **Audit Access**: View system audit logs

### Requesting Access

If you need additional permissions:

1. **Identify Required Access**
   - Determine what specific permissions you need
   - Understand why you need this access

2. **Contact Your Manager**
   - Discuss your access requirements
   - Get approval for additional permissions

3. **Submit Request**
   - Email your request to your administrator
   - Include business justification
   - Specify exact permissions needed

4. **Wait for Approval**
   - Administrator reviews and approves request
   - You'll receive notification when access is granted
   - Log out and back in to see new permissions

## Account Management

### Profile Settings

#### Personal Information

1. **Access Profile**
   - Click your profile picture/name
   - Select "Profile Settings" or "Account Settings"

2. **Update Information**
   - **Name**: First and last name
   - **Email**: Primary email address
   - **Phone**: Contact phone number
   - **Title**: Job title or position
   - **Department**: Your department or team

3. **Profile Picture**
   - Click "Change Picture"
   - Upload new image (JPG, PNG, max 5MB)
   - Crop and adjust as needed
   - Save changes

#### Preferences

1. **Display Settings**
   - **Language**: Choose interface language
   - **Timezone**: Set your local timezone
   - **Date Format**: Select preferred date format
   - **Currency**: Choose default currency

2. **Notification Settings**
   - **Email Notifications**: Choose what emails to receive
   - **In-App Notifications**: Configure platform notifications
   - **SMS Alerts**: Set up text message alerts
   - **Frequency**: Daily, weekly, or real-time

3. **Privacy Settings**
   - **Profile Visibility**: Control who can see your profile
   - **Activity Status**: Show/hide when you're online
   - **Data Sharing**: Control data sharing preferences

### Security Settings

#### Password Management

1. **Change Password**
   - Go to Security Settings
   - Click "Change Password"
   - Enter current password
   - Enter new password (twice)
   - Save changes

2. **Password Requirements**
   - Minimum 8 characters
   - At least one uppercase letter
   - At least one lowercase letter
   - At least one number
   - At least one special character

#### Session Management

1. **Active Sessions**
   - View all active login sessions
   - See device, location, and last activity
   - End suspicious or old sessions

2. **Session Settings**
   - **Auto-logout**: Set inactivity timeout
   - **Remember Me**: Control persistent sessions
   - **Concurrent Sessions**: Limit number of active sessions

#### Login History

1. **View Login Activity**
   - See recent login attempts
   - Check for suspicious activity
   - Review failed login attempts

2. **Security Alerts**
   - Get notified of unusual login activity
   - Receive alerts for new device logins
   - Monitor failed login attempts

### Data and Privacy

#### Data Export

1. **Request Data Export**
   - Go to Privacy Settings
   - Click "Export My Data"
   - Choose data types to include
   - Submit request

2. **Download Data**
   - Receive email when export is ready
   - Download ZIP file with your data
   - Data includes profile, projects, and activity

#### Account Deletion

1. **Request Account Deletion**
   - Go to Privacy Settings
   - Click "Delete Account"
   - Confirm you want to delete
   - Enter password to verify

2. **Deletion Process**
   - Account marked for deletion
   - 30-day grace period to recover
   - Permanent deletion after 30 days
   - Some data may be retained for legal compliance

## Security Best Practices

### Password Security

#### Creating Strong Passwords

- **Length**: Use at least 12 characters
- **Complexity**: Mix uppercase, lowercase, numbers, symbols
- **Uniqueness**: Don't reuse passwords from other sites
- **Avoid**: Personal information, common words, patterns

#### Password Management

- **Password Manager**: Use tools like 1Password, LastPass, or Bitwarden
- **Unique Passwords**: Different password for every account
- **Regular Updates**: Change passwords periodically
- **Secure Storage**: Never write passwords down or share them

### Device Security

#### Secure Devices

- **Lock Screen**: Use PIN, password, or biometric lock
- **Auto-Lock**: Set short auto-lock timeout
- **Updates**: Keep operating system and browsers updated
- **Antivirus**: Use reputable antivirus software

#### Browser Security

- **HTTPS**: Always verify secure connection (lock icon)
- **Bookmarks**: Bookmark login page to avoid phishing
- **Private Browsing**: Use for shared or public computers
- **Clear Data**: Clear cookies and cache regularly

### Network Security

#### Safe Networks

- **Trusted Networks**: Use secure, password-protected WiFi
- **Avoid Public WiFi**: Don't use for sensitive activities
- **VPN**: Use company VPN when working remotely
- **Mobile Data**: Prefer cellular over public WiFi

#### Recognizing Threats

- **Phishing Emails**: Be suspicious of unexpected emails
- **Fake Websites**: Verify URL before entering credentials
- **Social Engineering**: Don't share login information
- **Suspicious Activity**: Report unusual account activity

### Account Monitoring

#### Regular Checks

- **Login History**: Review monthly for suspicious activity
- **Active Sessions**: Check and end unknown sessions
- **Email Alerts**: Enable and monitor security notifications
- **Profile Changes**: Verify any unexpected profile updates

#### Incident Response

1. **Suspected Compromise**
   - Change password immediately
   - End all active sessions
   - Enable MFA if not already active
   - Contact support

2. **Lost Device**
   - End sessions from lost device
   - Change password as precaution
   - Monitor account for suspicious activity
   - Report to IT if company device

## Troubleshooting

### Common Login Issues

#### "Invalid Credentials" Error

**Possible Causes:**
- Incorrect email or password
- Account locked due to failed attempts
- Account disabled or suspended

**Solutions:**
1. Verify email address is correct
2. Check if Caps Lock is on
3. Try password reset if unsure
4. Contact administrator if account locked

#### "Account Not Found" Error

**Possible Causes:**
- Email address not registered
- Account deleted or deactivated
- Using wrong email address

**Solutions:**
1. Verify correct email address
2. Check if you have multiple email addresses
3. Contact administrator to verify account status
4. Register new account if needed

#### MFA Code Not Working

**Possible Causes:**
- Code expired (codes expire after 30 seconds)
- Clock synchronization issue
- Wrong authenticator app

**Solutions:**
1. Generate new code and try again
2. Check device time is correct
3. Use backup codes if available
4. Contact support to reset MFA

### Browser Issues

#### Page Won't Load

**Solutions:**
1. Refresh the page (Ctrl+F5 or Cmd+Shift+R)
2. Clear browser cache and cookies
3. Try different browser
4. Check internet connection
5. Disable browser extensions temporarily

#### Login Button Not Working

**Solutions:**
1. Enable JavaScript in browser
2. Disable ad blockers temporarily
3. Clear browser cache
4. Try incognito/private browsing mode
5. Update browser to latest version

### SSO Issues

#### Redirect Loop

**Solutions:**
1. Clear browser cookies for both sites
2. Try different browser
3. Contact IT administrator
4. Check if VPN is required

#### "Access Denied" After SSO

**Solutions:**
1. Verify you should have platform access
2. Contact your manager or administrator
3. Check if account provisioning is complete
4. Try logging out and back in

### Mobile App Issues

#### App Won't Open

**Solutions:**
1. Force close and reopen app
2. Restart device
3. Update app to latest version
4. Clear app cache/data
5. Reinstall app if necessary

#### Sync Issues

**Solutions:**
1. Check internet connection
2. Force sync in app settings
3. Log out and back in
4. Update app to latest version

## Frequently Asked Questions

### General Questions

**Q: Why did the login process change?**
A: We upgraded to Auth0 for enhanced security, better user experience, and enterprise features like SSO and advanced MFA.

**Q: Do I need to create a new account?**
A: No, existing accounts are automatically migrated. Use your existing email address to log in.

**Q: Can I use my old password?**
A: Yes, your existing password continues to work. However, we recommend updating to a stronger password.

**Q: Is my data safe during the migration?**
A: Yes, all data is securely migrated with no loss of information. Enhanced security measures are now in place.

### Authentication Questions

**Q: Is MFA required?**
A: MFA is strongly recommended and may be required for certain roles or enterprise accounts.

**Q: Can I use multiple MFA methods?**
A: Yes, you can set up multiple methods (authenticator app, SMS, email) for redundancy.

**Q: What if I lose my MFA device?**
A: Use backup codes or contact your administrator to reset MFA. Always save backup codes securely.

**Q: How long do I stay logged in?**
A: Sessions last 24 hours by default, but you can adjust this in settings or use "Remember Me" for longer sessions.

### Enterprise Questions

**Q: How do I set up SSO for my organization?**
A: Contact our enterprise support team at enterprise@nextgen-fusion.com for SSO configuration assistance.

**Q: Can we customize the login page?**
A: Yes, enterprise customers can customize branding, colors, and logos on the login page.

**Q: How are user roles managed?**
A: Administrators can manage roles through the platform, or roles can be automatically assigned via SSO attributes.

**Q: Is there an API for user management?**
A: Yes, we provide REST APIs for user provisioning, role management, and authentication integration.

### Technical Questions

**Q: Which browsers are supported?**
A: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+. Mobile browsers on iOS 14+ and Android 10+.

**Q: Can I use the platform offline?**
A: Limited offline functionality is available in the mobile app. Full features require internet connection.

**Q: How do I integrate with our existing systems?**
A: We support SAML, OIDC, and REST API integrations. Contact our technical team for integration assistance.

**Q: Is there a mobile app?**
A: Yes, mobile apps are available for iOS and Android with full authentication support.

### Support Questions

**Q: How do I get help?**
A: Contact support@nextgen-fusion.com, use the in-app help chat, or contact your administrator.

**Q: What information should I include in support requests?**
A: Include your email address, description of the issue, browser/device information, and any error messages.

**Q: How quickly will I get a response?**
A: Standard support: 24 hours. Enterprise customers: 4 hours. Critical issues: 1 hour.

**Q: Is there user training available?**
A: Yes, we offer webinars, documentation, and on-site training for enterprise customers.

## Getting Help

### Support Channels

#### Email Support
- **General Support**: support@nextgen-fusion.com
- **Technical Issues**: technical@nextgen-fusion.com
- **Enterprise Support**: enterprise@nextgen-fusion.com
- **Security Issues**: security@nextgen-fusion.com

#### In-App Support
- Click the "Help" or "Support" button in the platform
- Use the chat widget for real-time assistance
- Access knowledge base and documentation

#### Phone Support (Enterprise Only)
- **US/Canada**: +1-800-NEXTGEN
- **UK**: +44-800-NEXTGEN
- **Australia**: +61-800-NEXTGEN
- **Hours**: 24/7 for critical issues, business hours for general support

### Self-Service Resources

#### Documentation
- **User Guide**: Complete platform documentation
- **Video Tutorials**: Step-by-step video guides
- **FAQ**: Frequently asked questions
- **API Documentation**: For developers and integrators

#### Community
- **User Forum**: Community discussions and tips
- **Webinars**: Regular training sessions
- **Newsletter**: Product updates and best practices

### Training and Onboarding

#### New User Onboarding
- **Welcome Email**: Getting started guide
- **Interactive Tutorial**: In-app guided tour
- **Quick Start Guide**: Essential features overview
- **Video Series**: Comprehensive training videos

#### Advanced Training
- **Webinars**: Monthly feature deep-dives
- **Certification Program**: Become a platform expert
- **Custom Training**: On-site training for enterprise customers
- **Train-the-Trainer**: Programs for internal champions

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Next Review**: 2024-04-15  
**Languages Available**: English, Spanish, Portuguese, Afrikaans  
**Support**: support@nextgen-fusion.com