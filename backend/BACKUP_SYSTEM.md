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
