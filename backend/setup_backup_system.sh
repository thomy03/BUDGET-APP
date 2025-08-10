#!/bin/bash

# Budget Famille v2.3 - Backup System Setup Script
# Purpose: Initialize and configure the complete backup management system
# Author: DevOps Team
# Date: 2025-08-10

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_FILE="/tmp/budget_app_cron"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Print header
print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}  Budget Famille v2.3 - Backup System Setup${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
}

# Make scripts executable
make_scripts_executable() {
    echo -e "${BLUE}Making backup scripts executable...${NC}"
    
    local scripts=(
        "organize_backups.sh"
        "backup_rotation.sh"
        "pre_migration_backup.sh"
        "restore_database.sh"
    )
    
    for script in "${scripts[@]}"; do
        local script_path="${SCRIPT_DIR}/${script}"
        if [[ -f "$script_path" ]]; then
            chmod +x "$script_path"
            echo -e "${GREEN}✓ Made executable: ${script}${NC}"
        else
            echo -e "${RED}✗ Script not found: ${script}${NC}"
        fi
    done
    
    echo ""
}

# Test backup organization
test_backup_organization() {
    echo -e "${BLUE}Testing backup organization...${NC}"
    
    # Run the organize backups script
    if "${SCRIPT_DIR}/organize_backups.sh"; then
        echo -e "${GREEN}✓ Backup organization completed successfully${NC}"
    else
        echo -e "${RED}✗ Backup organization failed${NC}"
        return 1
    fi
    
    echo ""
}

# Setup cron job for automated backups
setup_cron_job() {
    echo -e "${BLUE}Setting up automated backup cron job...${NC}"
    
    # Create cron entry
    cat > "$CRON_FILE" << EOF
# Budget Famille v2.3 - Automated Database Backups
# Daily backup at 2 AM
0 2 * * * cd "${SCRIPT_DIR}" && ./backup_rotation.sh daily >> /dev/null 2>&1

# Weekly cleanup at 3 AM on Sundays
0 3 * * 0 cd "${SCRIPT_DIR}" && ./backup_rotation.sh cleanup >> /dev/null 2>&1
EOF
    
    echo "Proposed cron job:"
    echo -e "${CYAN}"
    cat "$CRON_FILE"
    echo -e "${NC}"
    
    echo -e "${YELLOW}To install this cron job, run:${NC}"
    echo -e "${YELLOW}  crontab ${CRON_FILE}${NC}"
    echo ""
    
    read -p "Would you like to install the cron job now? (y/N): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if crontab "$CRON_FILE" 2>/dev/null; then
            echo -e "${GREEN}✓ Cron job installed successfully${NC}"
        else
            echo -e "${RED}✗ Failed to install cron job${NC}"
            echo -e "${YELLOW}You can manually install it later with: crontab ${CRON_FILE}${NC}"
        fi
    else
        echo -e "${YELLOW}Cron job not installed. You can install it later with: crontab ${CRON_FILE}${NC}"
    fi
    
    echo ""
}

# Create backup system documentation
create_documentation() {
    echo -e "${BLUE}Creating backup system documentation...${NC}"
    
    local doc_file="${SCRIPT_DIR}/BACKUP_SYSTEM.md"
    
    cat > "$doc_file" << 'EOF'
# Budget Famille v2.3 - Backup System Documentation

## Overview
Comprehensive database backup and restore system with automated rotation, pre-migration safety backups, and recovery procedures.

## Directory Structure
```
/backups/
├── daily/           # Daily automated backups (7-day retention)
├── weekly/          # Weekly backups (4-week retention)  
├── manual/          # Manual backups and migrated backups (90-day retention)
├── pre-migration/   # Pre-migration safety backups (30-day retention)
├── backup_manifest.txt      # Inventory of moved backups
├── backup_report_YYYYMMDD.txt  # Daily backup reports
└── *.log           # Operation logs
```

## Scripts

### 1. organize_backups.sh
**Purpose**: Initial setup - moves existing backup files to organized structure
**Usage**: `./organize_backups.sh`
**Features**:
- Creates backup directory structure
- Moves existing scattered backup files to /backups/manual/
- Verifies backup integrity
- Creates backup manifest

### 2. backup_rotation.sh  
**Purpose**: Daily automated backups with retention management
**Usage**: 
- `./backup_rotation.sh daily` - Daily backup routine
- `./backup_rotation.sh weekly` - Force weekly backup
- `./backup_rotation.sh manual` - Create manual backup
- `./backup_rotation.sh cleanup` - Clean old backups
- `./backup_rotation.sh report` - Generate backup report
- `./backup_rotation.sh health` - Check backup health

**Features**:
- Daily backups with 7-day retention
- Weekly backups (Sundays) with 4-week retention
- Automatic cleanup of old backups
- Backup integrity verification
- Health monitoring and alerting

### 3. pre_migration_backup.sh
**Purpose**: Safety backups before database migrations
**Usage**:
- `./pre_migration_backup.sh create "migration_id" "description"`
- `./pre_migration_backup.sh complete "migration_id"`
- `./pre_migration_backup.sh rollback "migration_id"`
- `./pre_migration_backup.sh cleanup [retention_days]`
- `./pre_migration_backup.sh status`

**Features**:
- Creates safety backup before migrations
- Migration locking to prevent concurrent migrations
- Detailed metadata and history tracking
- Rollback support

### 4. restore_database.sh
**Purpose**: Safe database restore with validation and rollback
**Usage**:
- `./restore_database.sh` - Interactive mode
- `./restore_database.sh from-file <backup_file>` - Restore specific backup
- `./restore_database.sh list [type]` - List available backups
- `./restore_database.sh validate <backup_file>` - Check backup integrity
- `./restore_database.sh history` - Show restore history

**Features**:
- Interactive backup selection
- Pre-restore safety backup
- Integrity validation
- Automatic rollback on failure

## Automated Setup

### Cron Jobs
```bash
# Daily backup at 2 AM
0 2 * * * cd "/path/to/backend" && ./backup_rotation.sh daily

# Weekly cleanup at 3 AM on Sundays  
0 3 * * 0 cd "/path/to/backend" && ./backup_rotation.sh cleanup
```

### Integration with Deployment
Add to your deployment scripts:
```bash
# Before migrations
BACKUP_PATH=$(./pre_migration_backup.sh create "v2.3.1" "Add user preferences")

# Run migrations here
# ...

# After successful migration
./pre_migration_backup.sh complete "v2.3.1"

# On migration failure
# ./pre_migration_backup.sh rollback "v2.3.1"
```

## Monitoring and Alerts

### Health Checks
- Run `./backup_rotation.sh health` to check system health
- Monitor log files for errors
- Verify daily backups are created
- Check disk space usage

### Key Metrics
- Daily backup success rate
- Backup file integrity
- Storage usage trends
- Recovery time objectives (RTO)

## Recovery Procedures

### Emergency Database Recovery
1. **Assessment**: `./restore_database.sh list`
2. **Validation**: `./restore_database.sh validate <backup_file>`
3. **Restore**: `./restore_database.sh from-file <backup_file>`

### Migration Rollback
1. Find pre-migration backup: `ls backups/pre-migration/`
2. Restore: `./restore_database.sh from-file <pre_migration_backup>`

## Best Practices

1. **Regular Testing**: Test restore procedures monthly
2. **Monitor Disk Space**: Ensure adequate space for backups
3. **Verify Integrity**: Check backup integrity regularly
4. **Document Changes**: Update this documentation for system changes
5. **Security**: Protect backup files with appropriate permissions

## Troubleshooting

### Common Issues
- **Permission Denied**: Ensure scripts are executable (`chmod +x *.sh`)
- **Database Locked**: Stop application before restore
- **Disk Full**: Clean old backups or increase storage
- **Corrupted Backup**: Use older backup or recreate

### Log Locations
- Organization: `/backups/backup_organization.log`
- Rotation: `/backups/rotation.log`  
- Pre-migration: `/backups/pre-migration/pre_migration.log`
- Restore: `/backups/restore.log`

## Support
For issues or questions, check the log files first, then review this documentation.
EOF
    
    echo -e "${GREEN}✓ Documentation created: $(basename "$doc_file")${NC}"
    echo ""
}

# Test backup creation
test_backup_creation() {
    echo -e "${BLUE}Testing backup creation...${NC}"
    
    if "${SCRIPT_DIR}/backup_rotation.sh" manual; then
        echo -e "${GREEN}✓ Manual backup created successfully${NC}"
    else
        echo -e "${RED}✗ Manual backup creation failed${NC}"
        return 1
    fi
    
    echo ""
}

# Display system status
show_system_status() {
    echo -e "${BLUE}Backup System Status:${NC}"
    echo ""
    
    # Check if backup directory exists
    if [[ -d "${SCRIPT_DIR}/backups" ]]; then
        echo -e "${GREEN}✓ Backup directory exists${NC}"
        
        # Show directory sizes
        for subdir in daily weekly manual pre-migration; do
            local dir_path="${SCRIPT_DIR}/backups/${subdir}"
            if [[ -d "$dir_path" ]]; then
                local file_count=$(find "$dir_path" -name "budget.db.backup_*" -type f | wc -l)
                local dir_size=$(du -sh "$dir_path" 2>/dev/null | cut -f1 || echo "0")
                echo -e "  ${subdir^}: ${file_count} files, ${dir_size}"
            fi
        done
        
        echo ""
    else
        echo -e "${RED}✗ Backup directory not found${NC}"
    fi
    
    # Check script permissions
    local scripts=("organize_backups.sh" "backup_rotation.sh" "pre_migration_backup.sh" "restore_database.sh")
    echo -e "${BLUE}Script Status:${NC}"
    for script in "${scripts[@]}"; do
        local script_path="${SCRIPT_DIR}/${script}"
        if [[ -f "$script_path" ]] && [[ -x "$script_path" ]]; then
            echo -e "${GREEN}✓ ${script}${NC}"
        else
            echo -e "${RED}✗ ${script}${NC}"
        fi
    done
    
    echo ""
}

# Main setup function
main() {
    local action="${1:-full}"
    
    print_header
    
    case "$action" in
        "full")
            make_scripts_executable
            test_backup_organization
            test_backup_creation
            create_documentation
            setup_cron_job
            show_system_status
            
            echo -e "${GREEN}=== Backup System Setup Complete ===${NC}"
            echo ""
            echo -e "${CYAN}Next Steps:${NC}"
            echo -e "1. Review the created BACKUP_SYSTEM.md documentation"
            echo -e "2. Test the restore process: ${YELLOW}./restore_database.sh${NC}"
            echo -e "3. Monitor the daily backup logs"
            echo -e "4. Consider testing the pre-migration backup workflow"
            ;;
            
        "scripts-only")
            make_scripts_executable
            ;;
            
        "test-organize")
            test_backup_organization
            ;;
            
        "cron")
            setup_cron_job
            ;;
            
        "docs")
            create_documentation
            ;;
            
        "status")
            show_system_status
            ;;
            
        *)
            echo "Usage: $0 {full|scripts-only|test-organize|cron|docs|status}"
            echo ""
            echo "Commands:"
            echo "  full          - Complete setup (default)"
            echo "  scripts-only  - Make scripts executable only"
            echo "  test-organize - Test backup organization"
            echo "  cron         - Setup cron job only"
            echo "  docs         - Create documentation only"
            echo "  status       - Show system status"
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"