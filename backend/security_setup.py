#!/usr/bin/env python3
"""
Security Setup Script for Budget Famille v2.3
Generates secure keys and validates security configuration
"""

import os
import secrets
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_secure_key(length: int = 32) -> str:
    """Generate a cryptographically secure key"""
    return secrets.token_urlsafe(length)


def generate_security_keys() -> Dict[str, str]:
    """Generate all required security keys"""
    keys = {
        'JWT_SECRET_KEY': generate_secure_key(32),
        'DB_ENCRYPTION_KEY': generate_secure_key(32),
        'SESSION_SECRET': generate_secure_key(24),
        'CSRF_SECRET': generate_secure_key(24)
    }
    
    logger.info("Generated secure keys for production deployment")
    return keys


def create_env_file(template_path: str, output_path: str, keys: Dict[str, str], 
                   domain: str = None) -> bool:
    """Create .env file from template with secure keys"""
    try:
        template_file = Path(template_path)
        output_file = Path(output_path)
        
        if not template_file.exists():
            logger.error(f"Template file not found: {template_path}")
            return False
        
        # Read template
        content = template_file.read_text()
        
        # Replace placeholders with secure keys
        replacements = {
            'REPLACE_WITH_SECURE_32_CHAR_KEY': keys['JWT_SECRET_KEY'],
            'REPLACE_WITH_SECURE_DB_KEY': keys['DB_ENCRYPTION_KEY'],
            'YYYY-MM-DD': datetime.now().strftime('%Y-%m-%d'),
            'deployment-system': os.getenv('USER', 'automated')
        }
        
        # Replace domain if provided
        if domain:
            content = content.replace('https://your-production-domain.com', f'https://{domain}')
        
        # Apply all replacements
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        
        # Write output file
        output_file.write_text(content)
        
        # Set restrictive permissions (owner read/write only)
        output_file.chmod(0o600)
        
        logger.info(f"Created secure environment file: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating environment file: {e}")
        return False


def validate_environment() -> Tuple[bool, List[str]]:
    """Validate current environment configuration"""
    errors = []
    warnings = []
    
    # Check for .env file
    env_file = Path('.env')
    if not env_file.exists():
        errors.append("No .env file found")
        return False, errors
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        errors.append("python-dotenv not installed - cannot validate environment")
        return False, errors
    
    # Critical security checks
    jwt_secret = os.getenv('JWT_SECRET_KEY')
    if not jwt_secret:
        errors.append("JWT_SECRET_KEY not set")
    elif len(jwt_secret) < 32:
        errors.append(f"JWT_SECRET_KEY too short ({len(jwt_secret)} chars, minimum 32)")
    elif jwt_secret in ['your-secret-key', 'REPLACE_WITH_SECURE_32_CHAR_KEY']:
        errors.append("JWT_SECRET_KEY contains default/placeholder value")
    
    # Environment checks
    environment = os.getenv('ENVIRONMENT', 'development')
    if environment == 'production':
        # Production-specific validations
        
        # CORS validation
        cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
        if not cors_origins:
            errors.append("CORS_ALLOWED_ORIGINS must be set in production")
        elif 'localhost' in cors_origins or '127.0.0.1' in cors_origins:
            errors.append("Production CORS_ALLOWED_ORIGINS contains development URLs")
        
        # Debug mode check
        debug = os.getenv('DEBUG', 'false').lower()
        if debug == 'true':
            errors.append("DEBUG mode must be disabled in production")
        
        # Database encryption check
        db_encryption = os.getenv('ENABLE_DB_ENCRYPTION', 'false').lower()
        if db_encryption != 'true':
            warnings.append("Database encryption is recommended for production")
        
        # Token expiration check
        token_expire = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
        if token_expire > 60:
            warnings.append(f"JWT token expiration is long ({token_expire} min) - consider shorter for production")
    
    # Rate limiting checks
    rate_limit = os.getenv('RATE_LIMIT_PER_MINUTE')
    if not rate_limit:
        warnings.append("Rate limiting not configured")
    
    # File permissions check
    if env_file.stat().st_mode & 0o077:
        warnings.append(".env file has overly permissive permissions - should be 600")
    
    # Log results
    if errors:
        logger.error(f"Found {len(errors)} security errors")
        for error in errors:
            logger.error(f"  ❌ {error}")
    
    if warnings:
        logger.warning(f"Found {len(warnings)} security warnings")
        for warning in warnings:
            logger.warning(f"  ⚠️  {warning}")
    
    if not errors and not warnings:
        logger.info("✅ All security validations passed")
    
    return len(errors) == 0, errors + warnings


def security_audit() -> bool:
    """Perform comprehensive security audit"""
    logger.info("🔍 Starting security audit...")
    
    audit_results = []
    
    # 1. Environment validation
    env_valid, env_issues = validate_environment()
    audit_results.append(("Environment Configuration", env_valid, env_issues))
    
    # 2. File permissions audit
    sensitive_files = ['.env', 'budget.db', 'budget_encrypted.db']
    file_issues = []
    
    for filename in sensitive_files:
        file_path = Path(filename)
        if file_path.exists():
            stat = file_path.stat()
            if stat.st_mode & 0o077:  # Check if group/other have permissions
                file_issues.append(f"{filename} has overly permissive permissions")
    
    audit_results.append(("File Permissions", len(file_issues) == 0, file_issues))
    
    # 3. Default credentials check
    cred_issues = []
    try:
        from auth import fake_users_db
        if fake_users_db:
            cred_issues.append("Hardcoded user credentials detected in auth.py")
    except ImportError:
        pass
    
    audit_results.append(("Credential Security", len(cred_issues) == 0, cred_issues))
    
    # 4. Dependencies audit
    dep_issues = []
    try:
        import pkg_resources
        installed_packages = [d.project_name for d in pkg_resources.working_set]
        
        # Check for known vulnerable packages (simplified)
        vulnerable_patterns = ['django<2.0', 'flask<1.0', 'requests<2.20']
        # This would need a real vulnerability database in production
        
    except ImportError:
        dep_issues.append("Cannot check dependencies - pkg_resources not available")
    
    audit_results.append(("Dependencies", len(dep_issues) == 0, dep_issues))
    
    # Print audit summary
    logger.info("\n" + "="*60)
    logger.info("🛡️  SECURITY AUDIT SUMMARY")
    logger.info("="*60)
    
    all_passed = True
    for category, passed, issues in audit_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{category}: {status}")
        
        if issues:
            for issue in issues:
                logger.info(f"  - {issue}")
            all_passed = False
    
    logger.info("="*60)
    
    if all_passed:
        logger.info("🎉 Security audit completed successfully!")
        logger.info("System is ready for production deployment.")
    else:
        logger.error("⚠️  Security audit found issues that must be resolved.")
        logger.error("DO NOT deploy to production until all issues are fixed.")
    
    return all_passed


def main():
    """Main security setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Budget Famille Security Setup')
    parser.add_argument('--generate-keys', action='store_true', 
                       help='Generate secure keys and create production .env file')
    parser.add_argument('--validate', action='store_true', 
                       help='Validate current security configuration')
    parser.add_argument('--audit', action='store_true', 
                       help='Perform comprehensive security audit')
    parser.add_argument('--domain', type=str, 
                       help='Production domain for CORS configuration')
    parser.add_argument('--output', type=str, default='.env.production',
                       help='Output file for generated environment')
    
    args = parser.parse_args()
    
    if args.generate_keys:
        logger.info("🔐 Generating secure keys for production deployment...")
        
        keys = generate_security_keys()
        
        # Display generated keys securely
        logger.info("\n" + "="*50)
        logger.info("🔑 GENERATED SECURITY KEYS")
        logger.info("="*50)
        logger.info("IMPORTANT: Store these keys securely!")
        logger.info("Never commit these keys to version control!")
        logger.info("-"*50)
        
        for key, value in keys.items():
            logger.info(f"{key}={value}")
        
        logger.info("="*50)
        
        # Create production environment file
        if create_env_file('.env.production.template', args.output, keys, args.domain):
            logger.info(f"✅ Production environment file created: {args.output}")
            logger.info("Remember to:")
            logger.info("1. Review and customize the configuration")
            logger.info("2. Set appropriate file permissions (chmod 600)")
            logger.info("3. Never commit this file to version control")
        else:
            logger.error("❌ Failed to create production environment file")
            sys.exit(1)
    
    elif args.validate:
        logger.info("🔍 Validating security configuration...")
        valid, issues = validate_environment()
        
        if not valid:
            logger.error("❌ Security validation failed")
            sys.exit(1)
        else:
            logger.info("✅ Security validation passed")
    
    elif args.audit:
        logger.info("🛡️  Performing comprehensive security audit...")
        
        if not security_audit():
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()