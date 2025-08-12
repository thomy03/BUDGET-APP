# Security Configuration Guide - Budget Famille v2.3

## 🛡️ Security Overview

This document provides comprehensive security configuration guidance for Budget Famille v2.3, addressing critical security issues identified in the security audit.

## ⚠️ Critical Security Issues Resolved

### 1. JWT Secret Key Management
- **Issue**: Hardcoded default JWT secrets
- **Resolution**: Mandatory secure key generation with validation
- **Implementation**: Enhanced `SecuritySettings` class with validation

### 2. User Authentication
- **Issue**: Hardcoded admin credentials
- **Resolution**: Database-backed user management with secure defaults
- **Implementation**: New `User` model with bcrypt hashing

### 3. CORS Security
- **Issue**: Overly permissive CORS settings
- **Resolution**: Environment-specific CORS policies
- **Implementation**: Production-safe CORS configuration

### 4. Rate Limiting
- **Issue**: No protection against brute force attacks
- **Resolution**: Comprehensive rate limiting middleware
- **Implementation**: Progressive backoff and IP blocking

## 🔧 Security Configuration

### Environment Setup

#### Development Environment
```bash
# Copy and customize the example file
cp .env.example .env

# Generate secure JWT key
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
```

#### Production Environment
```bash
# Use the security setup script
python security_setup.py --generate-keys --domain your-domain.com

# Or manually create from template
cp .env.production.template .env.production

# Generate keys manually
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('DB_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
```

### Database Migration

#### Migrate to Secure User Management
```bash
# Run the user migration script
python migrate_users.py

# This will:
# 1. Create users and user_sessions tables
# 2. Generate secure admin credentials
# 3. Display the generated password (store securely!)
```

#### Enable Database Encryption (Production)
```bash
# Set in environment
ENABLE_DB_ENCRYPTION=true
DB_ENCRYPTION_KEY=your_generated_32_char_key
```

### Security Validation

#### Validate Current Configuration
```bash
# Run security validation
python security_setup.py --validate

# Run comprehensive security audit
python security_setup.py --audit
```

## 🔐 Authentication Security

### Password Requirements
- Minimum 12 characters
- Must contain: uppercase, lowercase, number, special character
- Cannot be common weak passwords
- Bcrypt hashing with 12 rounds

### Account Lockout Policy
- 5 failed attempts: 15-minute lockout
- 10 failed attempts: 1-hour lockout
- 15 failed attempts: 24-hour lockout

### Session Management
- JWT tokens with configurable expiration
- Production recommendation: 15-30 minutes
- Session tracking in database
- Automatic cleanup of expired sessions

## 🚦 Rate Limiting

### Default Limits
- General requests: 60/minute
- Authentication requests: 10/minute
- Burst allowance: 10 requests
- IP blocking after 5 auth failures

### Production Limits (Recommended)
- General requests: 30/minute
- Authentication requests: 5/minute
- Burst allowance: 5 requests

### Configuration
```env
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_AUTH_PER_MINUTE=5
RATE_LIMIT_BURST_SIZE=5
```

## 🌐 CORS Security

### Development
Automatically allows localhost origins in development mode.

### Production
Must explicitly set allowed origins:
```env
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

## 🔒 Database Security

### Standard Database
- SQLite with WAL mode
- Connection timeouts and pooling
- Proper file permissions (600)

### Encrypted Database (Production)
- SQLCipher with AES-256 encryption
- PBKDF2 key derivation (256,000 iterations)
- HMAC-SHA512 authentication

### Configuration
```env
ENABLE_DB_ENCRYPTION=true
DB_ENCRYPTION_KEY=your_secure_32_char_key
```

## 🛠️ Security Middleware

### Rate Limiting Middleware
- IP-based sliding window algorithm
- Progressive authentication failure blocking
- Configurable limits per endpoint type

### Security Headers Middleware
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security
- Content-Security-Policy

### Request Validation Middleware
- Request size limits (10MB default)
- Content type validation
- Malformed request protection

## 📋 Security Checklist

### Pre-Production Checklist
- [ ] Generate unique JWT secret key (32+ characters)
- [ ] Generate unique database encryption key
- [ ] Set production CORS origins
- [ ] Enable database encryption
- [ ] Configure strict rate limiting
- [ ] Disable debug mode
- [ ] Set secure file permissions
- [ ] Run security audit
- [ ] Test authentication with new credentials
- [ ] Set up monitoring and alerting

### Ongoing Security Tasks
- [ ] Regular password rotations (quarterly)
- [ ] Security audit reviews (monthly)
- [ ] Dependency updates (weekly)
- [ ] Access reviews (quarterly)
- [ ] Log monitoring (daily)

## 🚨 Incident Response

### Suspected Breach
1. Immediately rotate all keys
2. Check access logs for suspicious activity
3. Force password reset for all users
4. Review and enhance security measures

### Failed Security Validation
1. Do not deploy to production
2. Fix all identified issues
3. Re-run security audit
4. Document remediation steps

## 📊 Monitoring and Alerting

### Security Metrics
- Failed authentication attempts
- Rate limit violations
- Suspicious IP addresses
- Database access anomalies

### Recommended Monitoring
- Set up log aggregation
- Configure security alerts
- Monitor authentication patterns
- Track unusual access patterns

## 🔧 Troubleshooting

### Common Issues

#### "JWT secret key too short"
```bash
# Generate proper length key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### "CORS_ALLOWED_ORIGINS not set in production"
```bash
# Set production origins
export CORS_ALLOWED_ORIGINS="https://yourdomain.com"
```

#### "Database encryption failed"
```bash
# Install pysqlcipher3
pip install pysqlcipher3

# Check encryption key length
echo $DB_ENCRYPTION_KEY | wc -c  # Should be 32+
```

#### "Rate limiting not working"
Check middleware registration in main app.py file.

## 📚 Additional Resources

- [OWASP Security Guidelines](https://owasp.org/)
- [JWT Security Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)
- [Python Security Guidelines](https://python.org/dev/security/)
- [SQLCipher Documentation](https://www.zetetic.net/sqlcipher/)

## 🆘 Support

For security-related questions or to report security vulnerabilities:
- Create a GitHub issue (for non-sensitive issues)
- Contact security team directly (for sensitive issues)
- Follow responsible disclosure practices

---

**Last Updated**: 2025-08-11  
**Version**: 2.3.0  
**Security Review**: Completed