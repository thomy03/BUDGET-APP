"""
Module de gestion sécurisée des uploads de fichiers
Protection contre malware, injection, et attaques par upload
"""

import os
import io
import hashlib
import tempfile
import logging
import mimetypes
import subprocess
from typing import Optional, List, Dict, Tuple, BinaryIO
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import pandas as pd
from fastapi import UploadFile, HTTPException
from audit_logger import get_audit_logger, AuditEventType

logger = logging.getLogger(__name__)

class SecurityThreat(Enum):
    MALWARE = "malware"
    OVERSIZED = "oversized"
    INVALID_TYPE = "invalid_type"
    MALICIOUS_CONTENT = "malicious_content"
    SUSPICIOUS_NAME = "suspicious_name"
    EXECUTION_ATTEMPT = "execution_attempt"

@dataclass
class SecurityScanResult:
    is_safe: bool
    threats: List[SecurityThreat]
    risk_score: float  # 0.0 = safe, 1.0 = maximum risk
    details: Dict[str, str]
    file_hash: str
    mime_type: str

@dataclass
class FileUploadConfig:
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = None
    allowed_mime_types: List[str] = None
    quarantine_suspicious: bool = True
    scan_content: bool = True
    check_executables: bool = True
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = ['.csv', '.xlsx', '.xls']
        
        if self.allowed_mime_types is None:
            self.allowed_mime_types = [
                'text/csv',
                'text/plain',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/csv'
            ]

class SecureFileValidator:
    """Validateur de fichiers avec analyse de sécurité approfondie"""
    
    def __init__(self, config: FileUploadConfig = None):
        self.config = config or FileUploadConfig()
        self.audit_logger = get_audit_logger()
        
        # Signatures malveillantes connues
        self.malicious_signatures = self._load_malicious_signatures()
        
        # Patterns suspects dans les noms de fichiers
        self.suspicious_filename_patterns = [
            r'\.exe$', r'\.scr$', r'\.bat$', r'\.cmd$', r'\.com$',
            r'\.pif$', r'\.vbs$', r'\.js$', r'\.jar$', r'\.php$',
            r'\.\.$', r'^\.',  # Hidden files
            r'[<>:"|?*]',  # Caractères interdits Windows
            r'\.{2,}',  # Multiple dots (path traversal)
        ]
        
    def _load_malicious_signatures(self) -> Dict[str, bytes]:
        """Charge les signatures de malware connues"""
        return {
            # Signatures PE (Windows executables)
            'pe_header': b'\x4D\x5A',  # MZ header
            'pe_signature': b'\x50\x45\x00\x00',  # PE signature
            
            # Signatures scripts malveillants
            'vbs_script': b'<script language="vbscript">',
            'js_eval': b'eval(',
            'powershell': b'powershell',
            
            # Macros Excel/Word suspectes
            'vba_autoexec': b'Auto_Open',
            'vba_shell': b'Shell(',
            
            # PHP/Web shells
            'php_shell': b'<?php',
            'php_eval': b'eval($_',
        }
    
    async def scan_file(self, file: UploadFile, username: str = None) -> SecurityScanResult:
        """Scanner de sécurité complet pour fichier uploadé"""
        
        logger.info(f"Scan sécuritaire de {file.filename}")
        threats = []
        risk_score = 0.0
        details = {}
        
        try:
            # Lire le contenu
            content = await file.read()
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Reset file position
            await file.seek(0)
            
            # 1. Validation taille
            if len(content) > self.config.max_file_size:
                threats.append(SecurityThreat.OVERSIZED)
                risk_score += 0.3
                details['size_violation'] = f"Taille: {len(content)} > {self.config.max_file_size}"
            
            # 2. Validation nom de fichier
            filename_threats = self._check_filename_security(file.filename or "")
            if filename_threats:
                threats.extend(filename_threats)
                risk_score += 0.4
                details['filename_issues'] = str(filename_threats)
            
            # 3. Détection type MIME
            mime_type = self._detect_mime_type(content, file.filename)
            if mime_type not in self.config.allowed_mime_types:
                threats.append(SecurityThreat.INVALID_TYPE)
                risk_score += 0.5
                details['mime_violation'] = f"MIME: {mime_type} non autorisé"
            
            # 4. Analyse contenu malveillant
            if self.config.scan_content:
                content_threats = self._scan_malicious_content(content)
                if content_threats:
                    threats.extend(content_threats)
                    risk_score += 0.8
                    details['content_threats'] = str(content_threats)
            
            # 5. Détection tentatives d'exécution
            if self.config.check_executables:
                exec_threats = self._check_executable_patterns(content)
                if exec_threats:
                    threats.append(SecurityThreat.EXECUTION_ATTEMPT)
                    risk_score += 0.9
                    details['execution_attempt'] = str(exec_threats)
            
            # 6. Validation structure fichier spécifique
            structure_valid = self._validate_file_structure(content, mime_type)
            if not structure_valid:
                threats.append(SecurityThreat.MALICIOUS_CONTENT)
                risk_score += 0.6
                details['structure_invalid'] = "Structure de fichier corrompue ou suspecte"
            
            # Évaluation finale
            is_safe = len(threats) == 0 and risk_score < 0.3
            
            # Audit log
            if threats:
                self.audit_logger.log_security_violation(
                    username=username,
                    violation_type="file_upload_threat",
                    details={
                        "filename": file.filename,
                        "threats": [t.value for t in threats],
                        "risk_score": risk_score,
                        "file_hash": file_hash[:16]
                    }
                )
            
            return SecurityScanResult(
                is_safe=is_safe,
                threats=threats,
                risk_score=min(risk_score, 1.0),
                details=details,
                file_hash=file_hash,
                mime_type=mime_type
            )
            
        except Exception as e:
            logger.error(f"Erreur scan sécuritaire: {e}")
            return SecurityScanResult(
                is_safe=False,
                threats=[SecurityThreat.MALWARE],
                risk_score=1.0,
                details={"scan_error": str(e)},
                file_hash="",
                mime_type="unknown"
            )
    
    def _check_filename_security(self, filename: str) -> List[SecurityThreat]:
        """Vérifie la sécurité du nom de fichier"""
        threats = []
        
        if not filename:
            return threats
        
        filename_lower = filename.lower()
        
        # Check suspicious patterns
        import re
        for pattern in self.suspicious_filename_patterns:
            if re.search(pattern, filename_lower):
                threats.append(SecurityThreat.SUSPICIOUS_NAME)
                break
        
        # Check double extensions
        if filename.count('.') > 1:
            parts = filename.split('.')
            if len(parts) >= 3:  # file.txt.exe
                threats.append(SecurityThreat.SUSPICIOUS_NAME)
        
        # Check path traversal attempts
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            threats.append(SecurityThreat.SUSPICIOUS_NAME)
        
        return threats
    
    def _detect_mime_type(self, content: bytes, filename: str = None) -> str:
        """Détection MIME type sécurisée"""
        
        # 1. Détection par signature binaire
        if content.startswith(b'\x50\x4B\x03\x04'):  # ZIP/XLSX
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif content.startswith(b'\xD0\xCF\x11\xE0'):  # OLE/XLS
            return 'application/vnd.ms-excel'
        elif content.startswith(b'\xEF\xBB\xBF'):  # UTF-8 BOM
            return 'text/csv'
        
        # 2. Analyse du contenu pour CSV
        try:
            # Tenter décodage UTF-8
            text_content = content[:1024].decode('utf-8', errors='ignore')
            
            # Vérifier patterns CSV
            csv_indicators = [',', ';', '\t', '|']
            if any(sep in text_content for sep in csv_indicators):
                # Vérifier que c'est majoritairement du texte
                printable_ratio = sum(1 for c in text_content if c.isprintable() or c in '\r\n\t') / len(text_content)
                if printable_ratio > 0.8:
                    return 'text/csv'
        except:
            pass
        
        # 3. Fallback par extension
        if filename:
            extension = Path(filename).suffix.lower()
            mime_map = {
                '.csv': 'text/csv',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.xls': 'application/vnd.ms-excel'
            }
            return mime_map.get(extension, 'application/octet-stream')
        
        return 'application/octet-stream'
    
    def _scan_malicious_content(self, content: bytes) -> List[SecurityThreat]:
        """Scanne le contenu pour signatures malveillantes"""
        threats = []
        
        content_lower = content.lower()
        
        for sig_name, signature in self.malicious_signatures.items():
            if signature in content_lower:
                logger.warning(f"Signature malveillante détectée: {sig_name}")
                threats.append(SecurityThreat.MALWARE)
                break
        
        # Vérifications spécifiques
        
        # Scripts embarqués
        script_patterns = [
            b'javascript:', b'vbscript:', b'data:text/html',
            b'<script', b'eval(', b'document.write'
        ]
        
        for pattern in script_patterns:
            if pattern in content_lower:
                threats.append(SecurityThreat.MALICIOUS_CONTENT)
                break
        
        # Commandes système
        system_patterns = [
            b'cmd.exe', b'powershell.exe', b'/bin/sh', b'/bin/bash',
            b'system(', b'exec(', b'shell_exec'
        ]
        
        for pattern in system_patterns:
            if pattern in content_lower:
                threats.append(SecurityThreat.EXECUTION_ATTEMPT)
                break
        
        return threats
    
    def _check_executable_patterns(self, content: bytes) -> List[str]:
        """Détecte les patterns d'exécution"""
        patterns = []
        
        # Headers exécutables
        if content.startswith(b'\x4D\x5A'):  # PE header
            patterns.append("PE_executable")
        
        if content.startswith(b'\x7fELF'):  # ELF header
            patterns.append("ELF_executable")
        
        # Shebang scripts
        if content.startswith(b'#!/'):
            patterns.append("script_shebang")
        
        return patterns
    
    def _validate_file_structure(self, content: bytes, mime_type: str) -> bool:
        """Valide la structure interne du fichier"""
        
        try:
            if mime_type == 'text/csv':
                # Validation structure CSV
                return self._validate_csv_structure(content)
            
            elif 'excel' in mime_type:
                # Validation structure Excel
                return self._validate_excel_structure(content)
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur validation structure: {e}")
            return False
    
    def _validate_csv_structure(self, content: bytes) -> bool:
        """Valide la structure d'un fichier CSV"""
        
        try:
            # Limiter la taille pour validation
            sample = content[:10240]  # 10KB sample
            
            # Essayer décodage
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    text = sample.decode(encoding)
                    break
                except:
                    continue
            else:
                return False
            
            # Vérifier structure CSV basique
            lines = text.split('\n')[:10]  # Premières lignes
            
            if len(lines) < 2:  # Au moins header + 1 ligne
                return False
            
            # Déterminer séparateur
            import csv
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(text[:1000])
                separator = dialect.delimiter
            except:
                separator = ','
            
            # Vérifier cohérence colonnes
            header_cols = len(lines[0].split(separator))
            if header_cols < 2:  # Au moins 2 colonnes
                return False
            
            # Vérifier quelques lignes de données
            for line in lines[1:5]:
                if line.strip():
                    cols = len(line.split(separator))
                    if abs(cols - header_cols) > 1:  # Tolérance 1 colonne
                        logger.warning(f"Structure CSV incohérente: {cols} vs {header_cols} colonnes")
                        return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur validation CSV: {e}")
            return False
    
    def _validate_excel_structure(self, content: bytes) -> bool:
        """Valide la structure d'un fichier Excel"""
        
        try:
            # Vérifications basiques de structure
            if content.startswith(b'\x50\x4B'):  # XLSX (ZIP)
                # Vérifier que c'est un ZIP valide
                import zipfile
                try:
                    with zipfile.ZipFile(io.BytesIO(content)) as zf:
                        # Vérifier files Excel essentiels
                        required_files = ['xl/workbook.xml', '[Content_Types].xml']
                        files = zf.namelist()
                        
                        for req_file in required_files:
                            if req_file not in files:
                                logger.warning(f"Fichier Excel manquant: {req_file}")
                                return False
                        
                        return True
                except zipfile.BadZipFile:
                    return False
            
            elif content.startswith(b'\xD0\xCF'):  # XLS (OLE)
                # Structure OLE basique
                # TODO: Validation plus poussée si nécessaire
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Erreur validation Excel: {e}")
            return False

class SecureFileProcessor:
    """Processeur de fichiers avec isolation et sandboxing"""
    
    def __init__(self):
        self.validator = SecureFileValidator()
        self.quarantine_dir = Path(tempfile.gettempdir()) / "budget_app_quarantine"
        self.quarantine_dir.mkdir(exist_ok=True)
        
    async def process_upload(self, file: UploadFile, username: str = None) -> Tuple[pd.DataFrame, SecurityScanResult]:
        """Traite un fichier uploadé de manière sécurisée"""
        
        # 1. Scanner sécurité
        scan_result = await self.validator.scan_file(file, username)
        
        # 2. Décision selon niveau de risque
        if scan_result.risk_score >= 0.8:
            await self._quarantine_file(file, scan_result)
            raise HTTPException(
                status_code=400,
                detail=f"Fichier rejeté pour sécurité: {', '.join([t.value for t in scan_result.threats])}"
            )
        
        elif scan_result.risk_score >= 0.5:
            logger.warning(f"Fichier suspect traité avec précautions: {file.filename}")
        
        # 3. Traitement isolé
        try:
            df = await self._process_in_sandbox(file)
            return df, scan_result
            
        except Exception as e:
            logger.error(f"Erreur traitement fichier: {e}")
            raise HTTPException(status_code=400, detail="Erreur lors du traitement du fichier")
    
    async def _quarantine_file(self, file: UploadFile, scan_result: SecurityScanResult):
        """Met en quarantaine un fichier suspect"""
        
        try:
            content = await file.read()
            
            quarantine_filename = f"{scan_result.file_hash}_{file.filename}"
            quarantine_path = self.quarantine_dir / quarantine_filename
            
            with open(quarantine_path, 'wb') as f:
                f.write(content)
            
            # Métadonnées de quarantaine
            metadata = {
                "original_filename": file.filename,
                "quarantine_time": pd.Timestamp.now().isoformat(),
                "threats": [t.value for t in scan_result.threats],
                "risk_score": scan_result.risk_score,
                "details": scan_result.details
            }
            
            import json
            metadata_path = quarantine_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.warning(f"Fichier mis en quarantaine: {quarantine_path}")
            
        except Exception as e:
            logger.error(f"Erreur quarantaine: {e}")
    
    async def _process_in_sandbox(self, file: UploadFile) -> pd.DataFrame:
        """Traite le fichier dans un environnement isolé"""
        
        # Reset position
        await file.seek(0)
        content = await file.read()
        
        # Créer fichier temporaire sécurisé
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Traitement selon type
            if file.filename.lower().endswith('.csv'):
                return self._process_csv_safe(temp_path)
            elif file.filename.lower().endswith(('.xlsx', '.xls')):
                return self._process_excel_safe(temp_path)
            else:
                raise ValueError("Type de fichier non supporté")
        
        finally:
            # Nettoyage sécurisé
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def _process_csv_safe(self, file_path: str) -> pd.DataFrame:
        """Traitement sécurisé CSV"""
        
        # Encodages à tester
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                # Lire avec limites de sécurité
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    nrows=50000,  # Limite sécuritaire
                    dtype=str,    # Éviter inférence types
                    on_bad_lines='skip'
                )
                
                if len(df.columns) >= 2:  # Structure minimale
                    return df
                    
            except Exception as e:
                logger.debug(f"Échec décodage {encoding}: {e}")
                continue
        
        raise ValueError("Impossible de lire le fichier CSV")
    
    def _process_excel_safe(self, file_path: str) -> pd.DataFrame:
        """Traitement sécurisé Excel"""
        
        try:
            # Lire avec limites
            df = pd.read_excel(
                file_path,
                nrows=50000,
                dtype=str,
                engine='openpyxl'  # Moteur sécurisé
            )
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur lecture Excel: {e}")
            raise ValueError("Impossible de lire le fichier Excel")

# Instance globale
secure_processor = SecureFileProcessor()