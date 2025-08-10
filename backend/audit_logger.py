"""
Système d'audit sécurisé pour l'application Budget Famille
Enregistre toutes les actions sensibles avec horodatage et utilisateur
"""

import os
import json
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

class AuditEventType(Enum):
    """Types d'événements d'audit"""
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    CONFIG_UPDATE = "CONFIG_UPDATE"
    TRANSACTION_IMPORT = "TRANSACTION_IMPORT"
    TRANSACTION_MODIFY = "TRANSACTION_MODIFY"
    FIXED_LINE_CREATE = "FIXED_LINE_CREATE"
    FIXED_LINE_UPDATE = "FIXED_LINE_UPDATE"
    FIXED_LINE_DELETE = "FIXED_LINE_DELETE"
    DATA_ACCESS = "DATA_ACCESS"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    DATABASE_MIGRATION = "DATABASE_MIGRATION"

class AuditLogger:
    def __init__(self):
        self.audit_file = os.getenv("AUDIT_LOG_FILE", "./audit.log")
        self.setup_audit_logging()
    
    def setup_audit_logging(self):
        """Configure le système de logging d'audit"""
        # Créer le répertoire si nécessaire
        audit_dir = Path(self.audit_file).parent
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurer le logger d'audit
        self.audit_logger = logging.getLogger("audit")
        self.audit_logger.setLevel(logging.INFO)
        
        # Éviter les doublons de handlers
        if not self.audit_logger.handlers:
            # Handler pour fichier d'audit
            file_handler = logging.FileHandler(self.audit_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # Format JSON structuré pour l'audit
            formatter = logging.Formatter(
                '%(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S UTC'
            )
            file_handler.setFormatter(formatter)
            
            self.audit_logger.addHandler(file_handler)
    
    def log_event(
        self,
        event_type: AuditEventType,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        resource: Optional[str] = None,
        success: bool = True
    ):
        """
        Enregistre un événement d'audit
        
        Args:
            event_type: Type d'événement (AuditEventType)
            username: Nom d'utilisateur impliqué
            ip_address: Adresse IP source
            user_agent: User-Agent du client
            details: Détails supplémentaires (sans données sensibles)
            resource: Ressource affectée
            success: Succès de l'opération
        """
        try:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": event_type.value,
                "username": username or "anonymous",
                "ip_address": self._hash_ip(ip_address) if ip_address else None,
                "user_agent_hash": self._hash_user_agent(user_agent) if user_agent else None,
                "resource": resource,
                "success": success,
                "details": self._sanitize_details(details or {}),
                "session_id": self._get_session_hash(username, ip_address),
            }
            
            # Enregistrer en JSON pour faciliter l'analyse
            audit_json = json.dumps(audit_entry, ensure_ascii=False)
            self.audit_logger.info(audit_json)
            
        except Exception as e:
            # Logger l'erreur sans révéler d'informations sensibles
            logging.error(f"Erreur logging audit: {str(e)[:100]}")
    
    def _hash_ip(self, ip_address: str) -> str:
        """Hash l'adresse IP pour la confidentialité"""
        if not ip_address:
            return None
        
        # Utiliser un salt pour la sécurité
        salt = os.getenv("AUDIT_SALT", "budget_app_audit_2024")
        return hashlib.sha256(f"{salt}:{ip_address}".encode()).hexdigest()[:16]
    
    def _hash_user_agent(self, user_agent: str) -> str:
        """Hash le User-Agent pour la confidentialité"""
        if not user_agent:
            return None
        
        salt = os.getenv("AUDIT_SALT", "budget_app_audit_2024")
        return hashlib.sha256(f"{salt}:{user_agent}".encode()).hexdigest()[:16]
    
    def _get_session_hash(self, username: Optional[str], ip_address: Optional[str]) -> str:
        """Génère un hash de session unique"""
        session_data = f"{username or 'anon'}:{ip_address or 'unknown'}:{datetime.utcnow().strftime('%Y%m%d%H')}"
        return hashlib.sha256(session_data.encode()).hexdigest()[:12]
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Nettoie les détails pour éviter l'exposition de données sensibles"""
        sensitive_keys = [
            'password', 'token', 'secret', 'key', 'auth',
            'credit_card', 'ssn', 'account_number', 'pin'
        ]
        
        sanitized = {}
        for key, value in details.items():
            key_lower = key.lower()
            
            # Masquer les clés sensibles
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            # Limiter la taille des valeurs
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "..."
            # Masquer les montants élevés (potentiellement sensibles)
            elif isinstance(value, (int, float)) and abs(value) > 100000:
                sanitized[key] = "[LARGE_AMOUNT]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def log_login_success(self, username: str, ip_address: str = None, user_agent: str = None):
        """Log une connexion réussie"""
        self.log_event(
            AuditEventType.LOGIN_SUCCESS,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    def log_login_failed(self, username: str, ip_address: str = None, reason: str = None):
        """Log une tentative de connexion échouée"""
        self.log_event(
            AuditEventType.LOGIN_FAILED,
            username=username,
            ip_address=ip_address,
            details={"failure_reason": reason},
            success=False
        )
    
    def log_data_modification(
        self,
        username: str,
        action: str,
        resource: str,
        resource_id: str = None,
        details: Dict[str, Any] = None
    ):
        """Log une modification de données"""
        event_mapping = {
            "create": AuditEventType.FIXED_LINE_CREATE,
            "update": AuditEventType.FIXED_LINE_UPDATE,
            "delete": AuditEventType.FIXED_LINE_DELETE,
        }
        
        event_type = event_mapping.get(action, AuditEventType.DATA_ACCESS)
        
        self.log_event(
            event_type,
            username=username,
            resource=f"{resource}:{resource_id}" if resource_id else resource,
            details=details,
            success=True
        )
    
    def log_security_violation(
        self,
        username: str = None,
        ip_address: str = None,
        violation_type: str = None,
        details: Dict[str, Any] = None
    ):
        """Log une violation de sécurité"""
        self.log_event(
            AuditEventType.SECURITY_VIOLATION,
            username=username,
            ip_address=ip_address,
            details={"violation_type": violation_type, **(details or {})},
            success=False
        )

# Instance globale du logger d'audit
audit_logger = AuditLogger()

def get_audit_logger() -> AuditLogger:
    """Récupère l'instance du logger d'audit"""
    return audit_logger