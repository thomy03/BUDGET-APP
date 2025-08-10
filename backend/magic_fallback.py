"""
Module de remplacement pour python-magic sur Windows
Détection de type MIME basée sur l'analyse des signatures binaires et extensions
"""

import os
from typing import Union


def from_buffer(buf: Union[bytes, bytearray], mime: bool = True) -> str:
    """
    Détecte le type MIME d'un buffer de données
    Version fallback compatible Windows sans libmagic
    """
    if not buf:
        return "application/octet-stream"
    
    b = bytes(buf)
    
    # Signatures ZIP/Office (XLSX est un ZIP)
    if len(b) >= 4 and b[:4] == b"PK\x03\x04":
        # Vérifier si c'est un XLSX en cherchant des indicateurs
        content_start = b[:512].decode('utf-8', errors='ignore').lower()
        if any(indicator in content_start for indicator in ['xl/', 'docprops/', 'content_types']):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return "application/zip"
    
    # Signature OLE2 (XLS classique)  
    if len(b) >= 8 and b[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        return "application/vnd.ms-excel"
    
    # Signature XLS alternative
    if len(b) >= 4 and b[:4] == b'\xd0\xcf\x11\xe0':
        return "application/vnd.ms-excel"
    
    # Exécutables Windows
    if len(b) >= 2 and b[:2] == b"MZ":
        return "application/x-executable"
    
    # PDF
    if len(b) >= 4 and b[:4] == b'%PDF':
        return "application/pdf"
        
    # Images communes
    if len(b) >= 3 and b[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    if len(b) >= 8 and b[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if len(b) >= 6 and b[:6] in [b'GIF87a', b'GIF89a']:
        return "image/gif"
    
    # BOM UTF-8
    if len(b) >= 3 and b[:3] == b'\xef\xbb\xbf':
        # C'est probablement un CSV avec BOM
        content = b[3:min(512, len(b))].decode('utf-8', errors='ignore').lower()
        if any(sep in content for sep in [',', ';', '\t']) or content.startswith(('date', 'dateop')):
            return "text/csv"
        return "text/plain"
    
    # Analyse textuelle pour détecter CSV
    try:
        # Essayer de décoder avec plusieurs encodages
        head = None
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                head = b[:min(1024, len(b))].decode(encoding, errors="ignore").lower().strip()
                break
            except:
                continue
        
        if head:
            first_line = head.split('\n')[0]
            
            # Headers CSV communs étendus
            csv_headers = [
                'dateop', 'date', 'dateval', 'libelle', 'label', 'description',
                'montant', 'amount', 'debit', 'credit', 'compte', 'account',
                'category', 'categorie', 'balance', 'solde', 'reference',
                'transaction', 'operation', 'details'
            ]
            
            # Séparateurs CSV
            csv_separators = [',', ';', '\t', '|']
            
            # Détecter CSV par multiple critères
            csv_indicators = [
                # Headers typiques
                any(header in first_line for header in csv_headers),
                # Présence de séparateurs multiples
                any(first_line.count(sep) >= 1 for sep in csv_separators),
                # Patterns de colonnes typiques
                any(pattern in head[:300] for pattern in ['date,', 'date;', 'montant,', 'amount,', 'description,']),
                # Structure de première ligne avec séparateurs
                len([c for c in first_line if c in csv_separators]) >= 2,
                # Format de date dans la première ligne
                any(date_pattern in first_line for date_pattern in ['2024', '2023', '2025', 'date']),
            ]
            
            if any(csv_indicators):
                return "text/csv"
                
            # Si c'est principalement ASCII/UTF-8 lisible avec séparateurs
            is_text = all(32 <= ord(c) <= 126 or c in '\n\r\t' for c in head[:200] if head)
            has_separators = any(sep in head[:200] for sep in csv_separators)
            
            if is_text and has_separators:
                return "text/csv"
            elif is_text:
                return "text/plain"
            
    except Exception:
        pass
    
    # Essayer avec d'autres encodages
    try:
        head = b[:min(512, len(b))].decode("latin-1", errors="ignore").lower()
        if any(sep in head for sep in [',', ';', '\t']):
            return "text/csv"
    except:
        pass
    
    # Fallback par défaut
    return "application/octet-stream"


def from_file(filename: str, mime: bool = True) -> str:
    """
    Détecte le type MIME d'un fichier
    Version fallback utilisant l'extension ET le contenu
    """
    try:
        with open(filename, 'rb') as f:
            header = f.read(2048)  # Lire plus pour une meilleure détection
        
        # D'abord essayer la détection par contenu
        mime_type = from_buffer(header, mime=mime)
        
        # Si pas de détection claire, utiliser l'extension
        if mime_type == "application/octet-stream":
            ext = os.path.splitext(filename)[1].lower()
            extension_mapping = {
                '.csv': 'text/csv',
                '.txt': 'text/plain',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.xls': 'application/vnd.ms-excel',
                '.pdf': 'application/pdf',
                '.zip': 'application/zip',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
            }
            mime_type = extension_mapping.get(ext, "application/octet-stream")
        
        return mime_type
        
    except (IOError, OSError) as e:
        # Si on ne peut pas lire le fichier, utiliser l'extension
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.csv':
            return 'text/csv'
        elif ext in ['.xlsx']:
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif ext == '.xls':
            return 'application/vnd.ms-excel'
        
        return "application/octet-stream"


# Compatibilité avec l'API python-magic
def Magic(mime=True):
    """Classe de compatibilité avec python-magic"""
    class MagicMock:
        def __init__(self, mime=True):
            self.mime = mime
            
        def from_buffer(self, buf):
            return from_buffer(buf, mime=self.mime)
            
        def from_file(self, filename):
            return from_file(filename, mime=self.mime)
    
    return MagicMock(mime=mime)


# Test de validation du module
if __name__ == "__main__":
    # Tests de base
    test_cases = [
        (b"PK\x03\x04", "application/zip"),
        (b"\xd0\xcf\x11\xe0", "application/vnd.ms-excel"),
        (b"dateOp,amount,label\n2024-01-01,100,test", "text/csv"),
        (b"\xef\xbb\xbfdate;montant\n", "text/csv"),
        (b"Hello World", "text/plain"),
    ]
    
    print("Test magic_fallback.py:")
    for data, expected in test_cases:
        result = from_buffer(data)
        status = "✅" if expected in result or result == expected else "❌"
        print(f"{status} {repr(data[:20])} -> {result}")