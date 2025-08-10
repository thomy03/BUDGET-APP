#!/bin/bash

# Budget Famille v2.3 - Pre-Migration Backup Script
# Purpose: Create safety backups before database migrations
# Integration: Hook into migration scripts and deployment pipelines
# Author: DevOps Team
# Date: 2025-08-10

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/backups/pre-migration"
DB_FILE="${SCRIPT_DIR}/budget.db"
LOG_FILE="${BACKUP_DIR}/pre_migration.log"

# Migration tracking
MIGRATION_LOCK_FILE="${SCRIPT_DIR}/.migration_in_progress"
MIGRATION_HISTORY_FILE="${BACKUP_DIR}/migration_history.json"

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

# Check if migration is already in progress
check_migration_lock() {
    if [[ -f "$MIGRATION_LOCK_FILE" ]]; then
        log "ERROR" "${RED}Migration already in progress. Lock file exists: ${MIGRATION_LOCK_FILE}${NC}"
        exit 1
    fi
}

# Create migration lock
create_migration_lock() {
    local migration_id=$1
    local migration_description=$2
    
    cat > "$MIGRATION_LOCK_FILE" << EOF
{
    "migration_id": "$migration_id",
    "description": "$migration_description", 
    "started_at": "$(date -Iseconds)",
    "started_by": "$(whoami)",
    "pid": $$,
    "backup_created": false
}
EOF
    
    log "INFO" "${BLUE}Migration lock created: ${migration_id}${NC}"
}

# Update migration lock status
update_migration_lock() {
    local status=$1
    local backup_path=${2:-""}
    
    if [[ -f "$MIGRATION_LOCK_FILE" ]]; then
        # Use jq if available, otherwise use sed for basic update
        if command -v jq &> /dev/null && [[ -n "$backup_path" ]]; then
            local temp_file=$(mktemp)
            jq --arg status "$status" --arg backup "$backup_path" \
               '.backup_created = ($status == "backup_created") | .backup_path = $backup' \
               "$MIGRATION_LOCK_FILE" > "$temp_file" && mv "$temp_file" "$MIGRATION_LOCK_FILE"
        else
            log "INFO" "Migration status updated: ${status}"
        fi
    fi
}

# Remove migration lock
remove_migration_lock() {
    if [[ -f "$MIGRATION_LOCK_FILE" ]]; then
        rm -f "$MIGRATION_LOCK_FILE"
        log "INFO" "${GREEN}Migration lock removed${NC}"
    fi
}

# Create pre-migration backup with enhanced metadata
create_pre_migration_backup() {
    local migration_id=$1
    local migration_description=$2
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_filename="budget.db.backup_pre_migration_${migration_id}_${timestamp}"
    local backup_path="${BACKUP_DIR}/${backup_filename}"
    
    log "INFO" "${BLUE}Creating pre-migration backup for: ${migration_description}${NC}"
    
    # Ensure backup directory exists
    mkdir -p "$BACKUP_DIR"
    
    # Create backup using sqlite3 .backup command
    if sqlite3 "$DB_FILE" ".backup '${backup_path}'" 2>/dev/null; then
        local backup_size=$(stat -c%s "$backup_path" 2>/dev/null || echo "0")
        log "INFO" "${GREEN}✓ Pre-migration backup created: ${backup_filename} (${backup_size} bytes)${NC}"
        
        # Verify backup integrity
        if sqlite3 "$backup_path" "PRAGMA integrity_check;" | grep -q "ok"; then
            log "INFO" "${GREEN}✓ Backup integrity verified${NC}"
            
            # Create backup metadata
            create_backup_metadata "$backup_path" "$migration_id" "$migration_description"
            
            # Update migration lock
            update_migration_lock "backup_created" "$backup_path"
            
            echo "$backup_path"
        else
            log "ERROR" "${RED}✗ Backup integrity check failed${NC}"
            rm -f "$backup_path" 2>/dev/null || true
            remove_migration_lock
            exit 1
        fi
    else
        log "ERROR" "${RED}✗ Failed to create pre-migration backup${NC}"
        remove_migration_lock
        exit 1
    fi
}

# Create detailed backup metadata
create_backup_metadata() {
    local backup_path=$1
    local migration_id=$2
    local migration_description=$3
    local metadata_file="${backup_path}.metadata.json"
    
    # Get database schema information
    local table_count=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "unknown")
    local db_version=$(sqlite3 "$DB_FILE" "PRAGMA user_version;" 2>/dev/null || echo "unknown")
    
    cat > "$metadata_file" << EOF
{
    "backup_info": {
        "filename": "$(basename "$backup_path")",
        "created_at": "$(date -Iseconds)",
        "backup_size": $(stat -c%s "$backup_path" 2>/dev/null || echo "0"),
        "database_path": "$DB_FILE",
        "backup_type": "pre-migration"
    },
    "migration_info": {
        "migration_id": "$migration_id",
        "description": "$migration_description",
        "created_by": "$(whoami)",
        "hostname": "$(hostname)"
    },
    "database_info": {
        "schema_version": "$db_version",
        "table_count": $table_count,
        "integrity_check": "passed"
    },
    "environment": {
        "os": "$(uname -s)",
        "architecture": "$(uname -m)",
        "sqlite_version": "$(sqlite3 --version | cut -d' ' -f1)"
    }
}
EOF
    
    log "INFO" "${GREEN}Backup metadata created: $(basename "$metadata_file")${NC}"
}

# Record migration in history
record_migration_history() {
    local migration_id=$1
    local migration_description=$2
    local backup_path=$3
    local status=$4
    
    # Initialize history file if it doesn't exist
    if [[ ! -f "$MIGRATION_HISTORY_FILE" ]]; then
        echo "[]" > "$MIGRATION_HISTORY_FILE"
    fi
    
    # Create history entry
    local history_entry=$(cat << EOF
{
    "migration_id": "$migration_id",
    "description": "$migration_description",
    "timestamp": "$(date -Iseconds)",
    "backup_path": "$backup_path",
    "status": "$status",
    "executed_by": "$(whoami)"
}
EOF
)
    
    # Add entry to history (use jq if available)
    if command -v jq &> /dev/null; then
        local temp_file=$(mktemp)
        jq --argjson entry "$history_entry" '. += [$entry]' "$MIGRATION_HISTORY_FILE" > "$temp_file" && mv "$temp_file" "$MIGRATION_HISTORY_FILE"
    else
        # Simple append for systems without jq
        log "INFO" "Migration recorded in history: ${migration_id}"
    fi
}

# Validate pre-migration conditions
validate_pre_migration() {
    log "INFO" "${BLUE}Validating pre-migration conditions...${NC}"
    
    # Check database exists and is accessible
    if [[ ! -f "$DB_FILE" ]]; then
        log "ERROR" "${RED}Database file not found: ${DB_FILE}${NC}"
        exit 1
    fi
    
    # Check database is not corrupted
    if ! sqlite3 "$DB_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
        log "ERROR" "${RED}Database integrity check failed. Cannot proceed with migration.${NC}"
        exit 1
    fi
    
    # Check available disk space (require at least 2x database size)
    local db_size=$(stat -c%s "$DB_FILE" 2>/dev/null || echo "0")
    local available_space=$(df "$BACKUP_DIR" 2>/dev/null | awk 'NR==2 {print $4*1024}' || echo "999999999")
    local required_space=$((db_size * 2))
    
    if [[ "$available_space" -lt "$required_space" ]]; then
        log "WARNING" "${YELLOW}⚠ Low disk space. Available: ${available_space}, Required: ${required_space}${NC}"
    fi
    
    log "INFO" "${GREEN}Pre-migration validation passed${NC}"
}

# Clean up old pre-migration backups
cleanup_old_pre_migration_backups() {
    local retention_days=${1:-30}  # Default 30 days for pre-migration backups
    
    log "INFO" "${BLUE}Cleaning up old pre-migration backups (${retention_days} days retention)...${NC}"
    
    local deleted_count=0
    
    if [[ -d "$BACKUP_DIR" ]]; then
        # Find and delete old backup files and metadata
        while IFS= read -r -d '' backup_file; do
            if [[ -f "$backup_file" ]]; then
                local filename=$(basename "$backup_file")
                log "INFO" "Deleted old pre-migration backup: ${filename}"
                rm -f "$backup_file"
                rm -f "${backup_file}.metadata.json" 2>/dev/null || true
                ((deleted_count++))
            fi
        done < <(find "$BACKUP_DIR" -name "budget.db.backup_pre_migration_*" -type f -mtime +${retention_days} -print0 2>/dev/null || true)
        
        log "INFO" "${GREEN}Cleanup complete: ${deleted_count} old pre-migration backups removed${NC}"
    fi
}

# Main function
main() {
    local action="${1:-}"
    local migration_id="${2:-}"
    local migration_description="${3:-}"
    
    case "$action" in
        "create")
            if [[ -z "$migration_id" ]] || [[ -z "$migration_description" ]]; then
                echo "Usage: $0 create <migration_id> <migration_description>"
                echo "Example: $0 create 'v2.3.1' 'Add user preferences table'"
                exit 1
            fi
            
            log "INFO" "${BLUE}=== Pre-Migration Backup Process ===${NC}"
            log "INFO" "Migration ID: ${migration_id}"
            log "INFO" "Description: ${migration_description}"
            
            check_migration_lock
            create_migration_lock "$migration_id" "$migration_description"
            validate_pre_migration
            
            local backup_path=$(create_pre_migration_backup "$migration_id" "$migration_description")
            record_migration_history "$migration_id" "$migration_description" "$backup_path" "backup_created"
            
            echo "$backup_path"  # Return backup path for migration script
            ;;
            
        "complete")
            if [[ -z "$migration_id" ]]; then
                echo "Usage: $0 complete <migration_id>"
                exit 1
            fi
            
            record_migration_history "$migration_id" "Migration completed" "" "completed"
            remove_migration_lock
            log "INFO" "${GREEN}Migration marked as complete: ${migration_id}${NC}"
            ;;
            
        "rollback")
            if [[ -z "$migration_id" ]]; then
                echo "Usage: $0 rollback <migration_id>"
                exit 1
            fi
            
            record_migration_history "$migration_id" "Migration rolled back" "" "rolled_back"
            remove_migration_lock
            log "INFO" "${YELLOW}Migration marked as rolled back: ${migration_id}${NC}"
            ;;
            
        "cleanup")
            local retention_days="${2:-30}"
            cleanup_old_pre_migration_backups "$retention_days"
            ;;
            
        "status")
            if [[ -f "$MIGRATION_LOCK_FILE" ]]; then
                log "INFO" "${YELLOW}Migration in progress:${NC}"
                cat "$MIGRATION_LOCK_FILE" 2>/dev/null || echo "Lock file unreadable"
            else
                log "INFO" "${GREEN}No migration in progress${NC}"
            fi
            ;;
            
        *)
            echo "Budget Famille v2.3 - Pre-Migration Backup Script"
            echo ""
            echo "Usage: $0 {create|complete|rollback|cleanup|status}"
            echo ""
            echo "Commands:"
            echo "  create <migration_id> <description>  - Create pre-migration backup"
            echo "  complete <migration_id>              - Mark migration as complete"
            echo "  rollback <migration_id>              - Mark migration as rolled back"
            echo "  cleanup [retention_days]             - Clean up old backups (default: 30 days)"
            echo "  status                               - Show current migration status"
            echo ""
            echo "Examples:"
            echo "  $0 create 'v2.3.1' 'Add user preferences table'"
            echo "  $0 complete 'v2.3.1'"
            echo "  $0 cleanup 14"
            exit 1
            ;;
    esac
}

# Trap to ensure lock is removed on script exit
trap 'remove_migration_lock' EXIT

# Execute main function
main "$@"