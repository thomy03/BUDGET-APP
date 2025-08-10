#!/bin/bash

# Budget Famille v2.3 - Database Restore Script
# Purpose: Safely restore database from backups with validation and rollback options
# Safety Features: Pre-restore backup, integrity checks, confirmation prompts
# Author: DevOps Team  
# Date: 2025-08-10

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/backups"
DB_FILE="${SCRIPT_DIR}/budget.db"
LOG_FILE="${BACKUP_DIR}/restore.log"
RESTORE_LOCK_FILE="${SCRIPT_DIR}/.restore_in_progress"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

# Check if restore is already in progress
check_restore_lock() {
    if [[ -f "$RESTORE_LOCK_FILE" ]]; then
        log "ERROR" "${RED}Restore already in progress. Lock file exists: ${RESTORE_LOCK_FILE}${NC}"
        echo "If you're sure no restore is running, remove the lock file:"
        echo "rm -f \"$RESTORE_LOCK_FILE\""
        exit 1
    fi
}

# Create restore lock
create_restore_lock() {
    local backup_file=$1
    
    cat > "$RESTORE_LOCK_FILE" << EOF
{
    "restore_started_at": "$(date -Iseconds)",
    "backup_file": "$backup_file",
    "started_by": "$(whoami)",
    "pid": $$
}
EOF
    
    log "INFO" "${BLUE}Restore lock created${NC}"
}

# Remove restore lock
remove_restore_lock() {
    if [[ -f "$RESTORE_LOCK_FILE" ]]; then
        rm -f "$RESTORE_LOCK_FILE"
        log "INFO" "${GREEN}Restore lock removed${NC}"
    fi
}

# List available backups with details
list_backups() {
    local backup_type=${1:-"all"}
    
    log "INFO" "${BLUE}Available backups:${NC}"
    echo ""
    
    local count=0
    
    for subdir in daily weekly manual pre-migration; do
        if [[ "$backup_type" != "all" ]] && [[ "$backup_type" != "$subdir" ]]; then
            continue
        fi
        
        local dir_path="${BACKUP_DIR}/${subdir}"
        if [[ -d "$dir_path" ]]; then
            echo -e "${CYAN}=== ${subdir^} Backups ===${NC}"
            
            # Find backup files and sort by modification time (newest first)
            while IFS= read -r -d '' backup_file; do
                if [[ -f "$backup_file" ]]; then
                    local filename=$(basename "$backup_file")
                    local filesize=$(stat -c%s "$backup_file" 2>/dev/null || echo "0")
                    local filedate=$(date -r "$backup_file" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "unknown")
                    local human_size=$(numfmt --to=iec "$filesize" 2>/dev/null || echo "${filesize}B")
                    
                    printf "%3d) %-50s %10s %s\n" $((++count)) "$filename" "$human_size" "$filedate"
                    
                    # Check for metadata file
                    if [[ -f "${backup_file}.metadata.json" ]]; then
                        if command -v jq &> /dev/null; then
                            local migration_id=$(jq -r '.migration_info.migration_id // "N/A"' "${backup_file}.metadata.json" 2>/dev/null || echo "N/A")
                            local description=$(jq -r '.migration_info.description // ""' "${backup_file}.metadata.json" 2>/dev/null || echo "")
                            if [[ "$migration_id" != "N/A" ]] && [[ -n "$description" ]]; then
                                printf "     └── Migration: %s - %s\n" "$migration_id" "$description"
                            fi
                        fi
                    fi
                fi
            done < <(find "$dir_path" -name "budget.db.backup_*" -type f -print0 2>/dev/null | sort -z -r)
            
            echo ""
        fi
    done
    
    if [[ "$count" -eq 0 ]]; then
        log "WARNING" "${YELLOW}No backup files found${NC}"
        return 1
    fi
    
    return 0
}

# Validate backup file
validate_backup() {
    local backup_file=$1
    
    log "INFO" "${BLUE}Validating backup file: $(basename "$backup_file")${NC}"
    
    # Check file exists
    if [[ ! -f "$backup_file" ]]; then
        log "ERROR" "${RED}Backup file not found: $backup_file${NC}"
        return 1
    fi
    
    # Check file is not empty
    local file_size=$(stat -c%s "$backup_file" 2>/dev/null || echo "0")
    if [[ "$file_size" -eq 0 ]]; then
        log "ERROR" "${RED}Backup file is empty${NC}"
        return 1
    fi
    
    # Check SQLite database integrity
    if sqlite3 "$backup_file" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        log "INFO" "${GREEN}✓ Backup file integrity check passed${NC}"
    else
        log "ERROR" "${RED}✗ Backup file integrity check failed${NC}"
        return 1
    fi
    
    # Check database schema
    local table_count=$(sqlite3 "$backup_file" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
    if [[ "$table_count" -gt 0 ]]; then
        log "INFO" "${GREEN}✓ Database contains ${table_count} tables${NC}"
    else
        log "WARNING" "${YELLOW}⚠ Database appears to have no tables${NC}"
    fi
    
    return 0
}

# Create safety backup before restore
create_safety_backup() {
    if [[ ! -f "$DB_FILE" ]]; then
        log "INFO" "${BLUE}No existing database file to backup${NC}"
        return 0
    fi
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local safety_backup="${BACKUP_DIR}/manual/budget.db.backup_pre_restore_${timestamp}"
    
    log "INFO" "${BLUE}Creating safety backup before restore...${NC}"
    
    # Ensure manual backup directory exists
    mkdir -p "${BACKUP_DIR}/manual"
    
    if sqlite3 "$DB_FILE" ".backup '${safety_backup}'" 2>/dev/null; then
        local backup_size=$(stat -c%s "$safety_backup" 2>/dev/null || echo "0")
        log "INFO" "${GREEN}✓ Safety backup created: $(basename "$safety_backup") (${backup_size} bytes)${NC}"
        echo "$safety_backup"
    else
        log "ERROR" "${RED}✗ Failed to create safety backup${NC}"
        return 1
    fi
}

# Perform database restore
perform_restore() {
    local backup_file=$1
    local safety_backup=$2
    
    log "INFO" "${BLUE}Starting database restore...${NC}"
    
    # Stop application if running (you may need to customize this)
    if pgrep -f "python.*app" > /dev/null 2>&1; then
        log "WARNING" "${YELLOW}⚠ Python application appears to be running. Consider stopping it first.${NC}"
        read -p "Continue with restore anyway? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "INFO" "Restore cancelled by user"
            return 1
        fi
    fi
    
    # Perform the restore
    if cp "$backup_file" "$DB_FILE" 2>/dev/null; then
        log "INFO" "${GREEN}✓ Database file restored${NC}"
        
        # Verify restored database
        if sqlite3 "$DB_FILE" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
            log "INFO" "${GREEN}✓ Restored database integrity verified${NC}"
            
            # Get basic stats from restored database
            local table_count=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "unknown")
            log "INFO" "${GREEN}Database restored successfully with ${table_count} tables${NC}"
            
            return 0
        else
            log "ERROR" "${RED}✗ Restored database failed integrity check${NC}"
            
            # Rollback to safety backup if available
            if [[ -n "$safety_backup" ]] && [[ -f "$safety_backup" ]]; then
                log "INFO" "${YELLOW}Rolling back to safety backup...${NC}"
                if cp "$safety_backup" "$DB_FILE" 2>/dev/null; then
                    log "INFO" "${GREEN}✓ Rollback completed${NC}"
                else
                    log "ERROR" "${RED}✗ Rollback failed - manual intervention required${NC}"
                fi
            fi
            
            return 1
        fi
    else
        log "ERROR" "${RED}✗ Failed to restore database file${NC}"
        return 1
    fi
}

# Interactive restore with confirmation
interactive_restore() {
    echo -e "${BLUE}=== Interactive Database Restore ===${NC}"
    echo ""
    
    # List available backups
    if ! list_backups; then
        exit 1
    fi
    
    # Get user selection
    echo -e "${CYAN}Select a backup to restore:${NC}"
    read -p "Enter backup number (or 'q' to quit): " -r backup_choice
    
    if [[ "$backup_choice" == "q" ]] || [[ "$backup_choice" == "Q" ]]; then
        log "INFO" "Restore cancelled by user"
        exit 0
    fi
    
    # Find the selected backup file
    local count=0
    local selected_backup=""
    
    for subdir in daily weekly manual pre-migration; do
        local dir_path="${BACKUP_DIR}/${subdir}"
        if [[ -d "$dir_path" ]]; then
            while IFS= read -r -d '' backup_file; do
                if [[ -f "$backup_file" ]]; then
                    ((count++))
                    if [[ "$count" -eq "$backup_choice" ]]; then
                        selected_backup="$backup_file"
                        break 2
                    fi
                fi
            done < <(find "$dir_path" -name "budget.db.backup_*" -type f -print0 2>/dev/null | sort -z -r)
        fi
    done
    
    if [[ -z "$selected_backup" ]]; then
        log "ERROR" "${RED}Invalid backup selection${NC}"
        exit 1
    fi
    
    # Confirm restore operation
    echo ""
    echo -e "${YELLOW}=== RESTORE CONFIRMATION ===${NC}"
    echo -e "Selected backup: ${GREEN}$(basename "$selected_backup")${NC}"
    echo -e "Backup date: ${GREEN}$(date -r "$selected_backup" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo 'unknown')${NC}"
    echo -e "Backup size: ${GREEN}$(stat -c%s "$selected_backup" 2>/dev/null | numfmt --to=iec || echo 'unknown')${NC}"
    
    if [[ -f "$DB_FILE" ]]; then
        echo -e "Current database: ${YELLOW}$(basename "$DB_FILE")${NC}"
        echo -e "Current size: ${YELLOW}$(stat -c%s "$DB_FILE" 2>/dev/null | numfmt --to=iec || echo 'unknown')${NC}"
    fi
    
    echo ""
    echo -e "${RED}WARNING: This will replace the current database!${NC}"
    echo -e "${GREEN}A safety backup will be created before restoration.${NC}"
    echo ""
    
    read -p "Are you sure you want to proceed? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "INFO" "Restore cancelled by user"
        exit 0
    fi
    
    # Proceed with restore
    restore_database_from_file "$selected_backup"
}

# Restore database from specified file
restore_database_from_file() {
    local backup_file=$1
    
    log "INFO" "${BLUE}=== Database Restore Process ===${NC}"
    log "INFO" "Backup file: $backup_file"
    
    check_restore_lock
    create_restore_lock "$backup_file"
    
    # Validate backup file
    if ! validate_backup "$backup_file"; then
        remove_restore_lock
        exit 1
    fi
    
    # Create safety backup
    local safety_backup=""
    if [[ -f "$DB_FILE" ]]; then
        safety_backup=$(create_safety_backup)
        if [[ $? -ne 0 ]]; then
            remove_restore_lock
            exit 1
        fi
    fi
    
    # Perform restore
    if perform_restore "$backup_file" "$safety_backup"; then
        log "INFO" "${GREEN}=== Database Restore Completed Successfully ===${NC}"
        if [[ -n "$safety_backup" ]]; then
            log "INFO" "Safety backup available at: $safety_backup"
        fi
    else
        log "ERROR" "${RED}=== Database Restore Failed ===${NC}"
        remove_restore_lock
        exit 1
    fi
}

# Show restore history
show_restore_history() {
    log "INFO" "${BLUE}Recent restore operations:${NC}"
    echo ""
    
    # Show last 10 restore operations from log
    if [[ -f "$LOG_FILE" ]]; then
        grep -E "\[INFO\].*=== Database Restore" "$LOG_FILE" | tail -10 | while IFS= read -r line; do
            echo "$line"
        done
    else
        log "INFO" "No restore history found"
    fi
}

# Main function
main() {
    local action="${1:-interactive}"
    
    case "$action" in
        "interactive"|"")
            interactive_restore
            ;;
            
        "from-file")
            local backup_file="${2:-}"
            if [[ -z "$backup_file" ]]; then
                echo "Usage: $0 from-file <backup_file_path>"
                exit 1
            fi
            
            if [[ ! -f "$backup_file" ]]; then
                log "ERROR" "${RED}Backup file not found: $backup_file${NC}"
                exit 1
            fi
            
            restore_database_from_file "$backup_file"
            ;;
            
        "list")
            local backup_type="${2:-all}"
            list_backups "$backup_type"
            ;;
            
        "validate")
            local backup_file="${2:-}"
            if [[ -z "$backup_file" ]]; then
                echo "Usage: $0 validate <backup_file_path>"
                exit 1
            fi
            
            if validate_backup "$backup_file"; then
                log "INFO" "${GREEN}Backup validation passed${NC}"
            else
                log "ERROR" "${RED}Backup validation failed${NC}"
                exit 1
            fi
            ;;
            
        "history")
            show_restore_history
            ;;
            
        "status")
            if [[ -f "$RESTORE_LOCK_FILE" ]]; then
                log "INFO" "${YELLOW}Restore in progress:${NC}"
                cat "$RESTORE_LOCK_FILE" 2>/dev/null || echo "Lock file unreadable"
            else
                log "INFO" "${GREEN}No restore in progress${NC}"
            fi
            ;;
            
        *)
            echo "Budget Famille v2.3 - Database Restore Script"
            echo ""
            echo "Usage: $0 {interactive|from-file|list|validate|history|status}"
            echo ""
            echo "Commands:"
            echo "  interactive                    - Interactive restore with backup selection"
            echo "  from-file <backup_file>        - Restore from specific backup file"
            echo "  list [daily|weekly|manual|pre-migration] - List available backups"
            echo "  validate <backup_file>         - Validate backup file integrity"
            echo "  history                        - Show restore operation history"
            echo "  status                         - Show current restore status"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Interactive mode"
            echo "  $0 from-file ./backups/daily/budget.db.backup_daily_20250810_120000"
            echo "  $0 list daily"
            echo "  $0 validate ./backups/manual/budget.db.backup_manual_20250810_100000"
            exit 1
            ;;
    esac
}

# Trap to ensure lock is removed on script exit
trap 'remove_restore_lock' EXIT

# Execute main function
main "$@"