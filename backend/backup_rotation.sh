#!/bin/bash

# Budget Famille v2.3 - Automated Backup Rotation Script
# Purpose: Create daily backups with automatic rotation and cleanup
# Retention Policy: Daily (7 days), Weekly (4 weeks)
# Author: DevOps Team
# Date: 2025-08-10

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/backups"
DB_FILE="${SCRIPT_DIR}/budget.db"
LOG_FILE="${BACKUP_DIR}/rotation.log"

# Retention policies (in days)
DAILY_RETENTION=7
WEEKLY_RETENTION=28
MANUAL_RETENTION=90

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "${BLUE}Checking prerequisites...${NC}"
    
    # Check if database exists
    if [[ ! -f "$DB_FILE" ]]; then
        log "ERROR" "${RED}Database file not found: ${DB_FILE}${NC}"
        exit 1
    fi
    
    # Check if sqlite3 is available
    if ! command -v sqlite3 &> /dev/null; then
        log "ERROR" "${RED}sqlite3 command not found. Please install sqlite3.${NC}"
        exit 1
    fi
    
    # Create backup directories if they don't exist
    mkdir -p "${BACKUP_DIR}"/{daily,weekly,manual,pre-migration}
    
    log "INFO" "${GREEN}Prerequisites check passed${NC}"
}

# Create database backup
create_backup() {
    local backup_type=$1
    local backup_subdir=$2
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_filename="budget.db.backup_${backup_type}_${timestamp}"
    local backup_path="${BACKUP_DIR}/${backup_subdir}/${backup_filename}"
    
    log "INFO" "${BLUE}Creating ${backup_type} backup...${NC}"
    
    # Use sqlite3 .backup command for consistent backup
    if sqlite3 "$DB_FILE" ".backup '${backup_path}'" 2>/dev/null; then
        local backup_size=$(stat -c%s "$backup_path" 2>/dev/null || echo "0")
        log "INFO" "${GREEN}✓ Backup created: ${backup_filename} (${backup_size} bytes)${NC}"
        
        # Verify backup integrity
        if sqlite3 "$backup_path" "PRAGMA integrity_check;" | grep -q "ok"; then
            log "INFO" "${GREEN}✓ Backup integrity verified${NC}"
            echo "$backup_path"
        else
            log "ERROR" "${RED}✗ Backup integrity check failed${NC}"
            rm -f "$backup_path" 2>/dev/null || true
            exit 1
        fi
    else
        log "ERROR" "${RED}✗ Failed to create backup${NC}"
        exit 1
    fi
}

# Clean old backups based on retention policy
cleanup_old_backups() {
    local backup_subdir=$1
    local retention_days=$2
    local backup_type=$3
    
    log "INFO" "${BLUE}Cleaning up old ${backup_type} backups (${retention_days} days retention)...${NC}"
    
    local backup_path="${BACKUP_DIR}/${backup_subdir}"
    local deleted_count=0
    
    if [[ -d "$backup_path" ]]; then
        # Find and delete files older than retention period
        while IFS= read -r -d '' backup_file; do
            if [[ -f "$backup_file" ]]; then
                local filename=$(basename "$backup_file")
                log "INFO" "Deleted old backup: ${filename}"
                rm -f "$backup_file"
                ((deleted_count++))
            fi
        done < <(find "$backup_path" -name "budget.db.backup_*" -type f -mtime +${retention_days} -print0 2>/dev/null || true)
        
        log "INFO" "${GREEN}Cleanup complete: ${deleted_count} old ${backup_type} backups removed${NC}"
    fi
}

# Create weekly backup (on Sundays)
create_weekly_backup() {
    local day_of_week=$(date '+%u')  # 1=Monday, 7=Sunday
    
    if [[ "$day_of_week" == "7" ]] || [[ "${1:-}" == "--force-weekly" ]]; then
        log "INFO" "${BLUE}Creating weekly backup...${NC}"
        create_backup "weekly" "weekly"
        cleanup_old_backups "weekly" "$WEEKLY_RETENTION" "weekly"
    fi
}

# Generate backup report
generate_backup_report() {
    log "INFO" "${BLUE}Generating backup report...${NC}"
    
    local report_file="${BACKUP_DIR}/backup_report_$(date '+%Y%m%d').txt"
    
    cat > "$report_file" << EOF
# Budget Famille v2.3 - Backup Report
# Generated: $(date)

## Backup Summary:
Daily Backups: $(find "${BACKUP_DIR}/daily" -name "budget.db.backup_*" -type f | wc -l) files
Weekly Backups: $(find "${BACKUP_DIR}/weekly" -name "budget.db.backup_*" -type f | wc -l) files  
Manual Backups: $(find "${BACKUP_DIR}/manual" -name "budget.db.backup_*" -type f | wc -l) files
Pre-migration Backups: $(find "${BACKUP_DIR}/pre-migration" -name "budget.db.backup_*" -type f | wc -l) files

## Storage Usage:
EOF
    
    for subdir in daily weekly manual pre-migration; do
        local dir_path="${BACKUP_DIR}/${subdir}"
        if [[ -d "$dir_path" ]]; then
            local size=$(du -sh "$dir_path" 2>/dev/null | cut -f1 || echo "0")
            echo "${subdir^}: ${size}" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF

## Recent Daily Backups:
EOF
    
    find "${BACKUP_DIR}/daily" -name "budget.db.backup_*" -type f -printf "%TY-%Tm-%Td %TH:%TM %f\n" 2>/dev/null | sort -r | head -5 >> "$report_file" || true
    
    log "INFO" "${GREEN}Backup report created: ${report_file}${NC}"
}

# Monitor backup health
monitor_backup_health() {
    log "INFO" "${BLUE}Monitoring backup health...${NC}"
    
    local daily_count=$(find "${BACKUP_DIR}/daily" -name "budget.db.backup_*" -type f -mtime -1 | wc -l)
    local weekly_count=$(find "${BACKUP_DIR}/weekly" -name "budget.db.backup_*" -type f -mtime -7 | wc -l)
    
    # Alert if no recent daily backup
    if [[ "$daily_count" -eq 0 ]]; then
        log "WARNING" "${YELLOW}⚠ No daily backup found in the last 24 hours${NC}"
    fi
    
    # Alert if no weekly backup (on Monday check)
    local day_of_week=$(date '+%u')
    if [[ "$day_of_week" == "1" ]] && [[ "$weekly_count" -eq 0 ]]; then
        log "WARNING" "${YELLOW}⚠ No weekly backup found in the last 7 days${NC}"
    fi
    
    # Check total backup count
    local total_backups=$(find "${BACKUP_DIR}" -name "budget.db.backup_*" -type f | wc -l)
    log "INFO" "${GREEN}Health check complete: ${total_backups} total backups${NC}"
}

# Main backup routine
main() {
    local action="${1:-daily}"
    
    log "INFO" "${BLUE}=== Budget Famille v2.3 Backup Rotation ===${NC}"
    log "INFO" "Action: ${action}"
    
    check_prerequisites
    
    case "$action" in
        "daily")
            create_backup "daily" "daily"
            cleanup_old_backups "daily" "$DAILY_RETENTION" "daily"
            create_weekly_backup
            cleanup_old_backups "manual" "$MANUAL_RETENTION" "manual"
            monitor_backup_health
            ;;
        "weekly")
            create_weekly_backup "--force-weekly"
            ;;
        "manual")
            create_backup "manual" "manual"
            ;;
        "cleanup")
            cleanup_old_backups "daily" "$DAILY_RETENTION" "daily"
            cleanup_old_backups "weekly" "$WEEKLY_RETENTION" "weekly"
            cleanup_old_backups "manual" "$MANUAL_RETENTION" "manual"
            ;;
        "report")
            generate_backup_report
            ;;
        "health")
            monitor_backup_health
            ;;
        *)
            echo "Usage: $0 {daily|weekly|manual|cleanup|report|health}"
            exit 1
            ;;
    esac
    
    log "INFO" "${GREEN}=== Backup Rotation Complete ===${NC}"
}

# Execute main function
main "$@"