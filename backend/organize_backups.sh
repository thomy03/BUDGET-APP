#!/bin/bash

# Budget Famille v2.3 - Backup Organization Script
# Purpose: Organize existing database backups and create proper folder structure
# Author: DevOps Team
# Date: 2025-08-10

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/backups"
DB_FILE="${SCRIPT_DIR}/budget.db"
LOG_FILE="${BACKUP_DIR}/backup_organization.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# Create backup directory structure
create_backup_structure() {
    log "INFO" "${BLUE}Creating backup directory structure...${NC}"
    
    mkdir -p "${BACKUP_DIR}/daily"
    mkdir -p "${BACKUP_DIR}/weekly"
    mkdir -p "${BACKUP_DIR}/manual"
    mkdir -p "${BACKUP_DIR}/pre-migration"
    
    # Set proper permissions
    chmod 755 "${BACKUP_DIR}"
    chmod 755 "${BACKUP_DIR}"/{daily,weekly,manual,pre-migration}
    
    log "INFO" "${GREEN}Backup directory structure created successfully${NC}"
}

# Move existing backup files
move_existing_backups() {
    log "INFO" "${BLUE}Moving existing backup files...${NC}"
    
    local moved_count=0
    local failed_count=0
    
    # Find all existing backup files
    for backup_file in "${SCRIPT_DIR}"/budget.db.backup_*; do
        if [[ -f "$backup_file" ]]; then
            local filename=$(basename "$backup_file")
            local target_file="${BACKUP_DIR}/manual/${filename}"
            
            if mv "$backup_file" "$target_file" 2>/dev/null; then
                log "INFO" "Moved: ${filename} -> manual/${filename}"
                ((moved_count++))
            else
                log "ERROR" "${RED}Failed to move: ${filename}${NC}"
                ((failed_count++))
            fi
        fi
    done
    
    log "INFO" "${GREEN}Backup organization complete: ${moved_count} files moved, ${failed_count} failures${NC}"
}

# Verify backup integrity
verify_backup_integrity() {
    log "INFO" "${BLUE}Verifying backup file integrity...${NC}"
    
    local verified_count=0
    local corrupted_count=0
    
    for backup_file in "${BACKUP_DIR}"/manual/budget.db.backup_*; do
        if [[ -f "$backup_file" ]]; then
            # Test SQLite database integrity
            if sqlite3 "$backup_file" "PRAGMA integrity_check;" > /dev/null 2>&1; then
                log "INFO" "✓ Verified: $(basename "$backup_file")"
                ((verified_count++))
            else
                log "WARNING" "${YELLOW}⚠ Corrupted or invalid: $(basename "$backup_file")${NC}"
                ((corrupted_count++))
            fi
        fi
    done
    
    log "INFO" "${GREEN}Integrity check complete: ${verified_count} valid, ${corrupted_count} corrupted${NC}"
}

# Create backup manifest
create_backup_manifest() {
    log "INFO" "${BLUE}Creating backup manifest...${NC}"
    
    local manifest_file="${BACKUP_DIR}/backup_manifest.txt"
    
    cat > "$manifest_file" << EOF
# Budget Famille v2.3 - Backup Manifest
# Generated: $(date)
# 
# Directory Structure:
# /backups/daily/        - Daily automated backups (7-day retention)
# /backups/weekly/       - Weekly backups (4-week retention)
# /backups/manual/       - Manual backups (moved from root directory)
# /backups/pre-migration/- Pre-migration safety backups

# Existing Backups Moved:
EOF
    
    for backup_file in "${BACKUP_DIR}"/manual/budget.db.backup_*; do
        if [[ -f "$backup_file" ]]; then
            local filename=$(basename "$backup_file")
            local filesize=$(stat -c%s "$backup_file" 2>/dev/null || echo "unknown")
            local filedate=$(date -r "$backup_file" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "unknown")
            echo "# ${filename} - Size: ${filesize} bytes - Date: ${filedate}" >> "$manifest_file"
        fi
    done
    
    log "INFO" "${GREEN}Backup manifest created: ${manifest_file}${NC}"
}

# Main execution
main() {
    log "INFO" "${BLUE}=== Budget Famille v2.3 Backup Organization ===${NC}"
    log "INFO" "Starting backup organization process..."
    
    # Initialize backup directory if it doesn't exist
    if [[ ! -d "$LOG_FILE" ]]; then
        mkdir -p "$(dirname "$LOG_FILE")"
    fi
    
    # Check if database exists
    if [[ ! -f "$DB_FILE" ]]; then
        log "WARNING" "${YELLOW}Main database file not found: ${DB_FILE}${NC}"
    fi
    
    # Execute organization steps
    create_backup_structure
    move_existing_backups
    verify_backup_integrity
    create_backup_manifest
    
    log "INFO" "${GREEN}=== Backup Organization Complete ===${NC}"
    log "INFO" "Next steps:"
    log "INFO" "1. Run ./backup_rotation.sh to set up automated rotation"
    log "INFO" "2. Add pre-migration hooks to your deployment scripts"
    log "INFO" "3. Schedule daily backups with cron"
}

# Execute main function
main "$@"