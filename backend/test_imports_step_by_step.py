#!/usr/bin/env python3
"""
Test des imports étape par étape pour isoler les problèmes
Teste chaque import individuellement pour identifier le point de blocage
"""
import sys
import traceback
import json
from typing import Dict, Any

def test_basic_imports() -> Dict[str, Any]:
    """Test des imports Python de base"""
    print("="*60)
    print("PHASE 1: IMPORTS PYTHON DE BASE")
    print("="*60)
    
    basic_imports = [
        ("io", "import io"),
        ("csv", "import csv"),
        ("re", "import re"),
        ("hashlib", "import hashlib"),
        ("datetime", "import datetime as dt"),
        ("logging", "import logging"),
        ("os", "import os"),
        ("uuid", "import uuid"),
        ("tempfile", "import tempfile"),
        ("html", "from html import escape"),
    ]
    
    results = {}
    for name, import_cmd in basic_imports:
        try:
            exec(import_cmd)
            print(f"✓ {name}: OK")
            results[name] = {"status": "OK"}
        except Exception as e:
            print(f"✗ {name}: ERREUR - {str(e)}")
            results[name] = {"status": "ERROR", "error": str(e)}
    
    return results

def test_typing_imports() -> Dict[str, Any]:
    """Test des imports typing"""
    print("\n" + "="*60)
    print("PHASE 2: IMPORTS TYPING")
    print("="*60)
    
    typing_imports = [
        ("typing_basic", "from typing import List, Optional, Dict, Union"),
        ("typing_any", "from typing import Any"),
    ]
    
    results = {}
    for name, import_cmd in typing_imports:
        try:
            exec(import_cmd)
            print(f"✓ {name}: OK")
            results[name] = {"status": "OK"}
        except Exception as e:
            print(f"✗ {name}: ERREUR - {str(e)}")
            results[name] = {"status": "ERROR", "error": str(e)}
    
    return results

def test_scientific_imports() -> Dict[str, Any]:
    """Test des imports scientifiques (numpy, pandas)"""
    print("\n" + "="*60)
    print("PHASE 3: IMPORTS SCIENTIFIQUES")
    print("="*60)
    
    scientific_imports = [
        ("numpy", "import numpy as np"),
        ("pandas", "import pandas as pd"),
    ]
    
    results = {}
    for name, import_cmd in scientific_imports:
        try:
            print(f"Test {name}...")
            exec(import_cmd)
            print(f"✓ {name}: OK")
            results[name] = {"status": "OK"}
        except Exception as e:
            print(f"✗ {name}: ERREUR - {str(e)}")
            results[name] = {"status": "ERROR", "error": str(e)}
            # Afficher plus de détails pour numpy/pandas
            if name in ["numpy", "pandas"]:
                print(f"  Détails erreur {name}:")
                traceback.print_exc()
    
    return results

def test_fastapi_imports() -> Dict[str, Any]:
    """Test des imports FastAPI"""
    print("\n" + "="*60)
    print("PHASE 4: IMPORTS FASTAPI")
    print("="*60)
    
    fastapi_imports = [
        ("fastapi_main", "from fastapi import FastAPI"),
        ("fastapi_upload", "from fastapi import UploadFile, File"),
        ("fastapi_http", "from fastapi import HTTPException"),
        ("fastapi_deps", "from fastapi import Depends, status"),
        ("fastapi_cors", "from fastapi.middleware.cors import CORSMiddleware"),
        ("fastapi_security", "from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm"),
    ]
    
    results = {}
    for name, import_cmd in fastapi_imports:
        try:
            print(f"Test {name}...")
            exec(import_cmd)
            print(f"✓ {name}: OK")
            results[name] = {"status": "OK"}
        except Exception as e:
            print(f"✗ {name}: ERREUR - {str(e)}")
            results[name] = {"status": "ERROR", "error": str(e)}
    
    return results

def test_validation_imports() -> Dict[str, Any]:
    """Test des imports de validation"""
    print("\n" + "="*60)
    print("PHASE 5: IMPORTS VALIDATION")
    print("="*60)
    
    validation_imports = [
        ("pydantic", "from pydantic import BaseModel"),
        ("pydantic_validator", "from pydantic import validator, Field"),
        ("email_validator", "from email_validator import validate_email, EmailNotValidError"),
    ]
    
    results = {}
    for name, import_cmd in validation_imports:
        try:
            print(f"Test {name}...")
            exec(import_cmd)
            print(f"✓ {name}: OK")
            results[name] = {"status": "OK"}
        except Exception as e:
            print(f"✗ {name}: ERREUR - {str(e)}")
            results[name] = {"status": "ERROR", "error": str(e)}
    
    return results

def test_database_imports() -> Dict[str, Any]:
    """Test des imports base de données"""
    print("\n" + "="*60)
    print("PHASE 6: IMPORTS BASE DE DONNÉES")
    print("="*60)
    
    database_imports = [
        ("sqlalchemy_create", "from sqlalchemy import create_engine"),
        ("sqlalchemy_columns", "from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Text"),
        ("sqlalchemy_orm", "from sqlalchemy.orm import sessionmaker, declarative_base, Session"),
    ]
    
    results = {}
    for name, import_cmd in database_imports:
        try:
            print(f"Test {name}...")
            exec(import_cmd)
            print(f"✓ {name}: OK")
            results[name] = {"status": "OK"}
        except Exception as e:
            print(f"✗ {name}: ERREUR - {str(e)}")
            results[name] = {"status": "ERROR", "error": str(e)}
    
    return results

def test_crypto_imports() -> Dict[str, Any]:
    """Test des imports cryptographiques"""
    print("\n" + "="*60)
    print("PHASE 7: IMPORTS CRYPTOGRAPHIQUES")
    print("="*60)
    
    crypto_imports = [
        ("dotenv", "from dotenv import load_dotenv"),
        ("pysqlcipher3", "import pysqlcipher3"),
        ("cryptography", "import cryptography"),
        ("passlib", "from passlib.context import CryptContext"),
        ("jose", "from jose import JWTError, jwt"),
    ]
    
    results = {}
    for name, import_cmd in crypto_imports:
        try:
            print(f"Test {name}...")
            exec(import_cmd)
            print(f"✓ {name}: OK")
            results[name] = {"status": "OK"}
        except Exception as e:
            print(f"✗ {name}: ERREUR - {str(e)}")
            results[name] = {"status": "ERROR", "error": str(e)}
            # Détails pour les imports critiques
            if name == "pysqlcipher3":
                print("  ATTENTION: pysqlcipher3 requis pour le chiffrement DB")
                traceback.print_exc()
    
    return results

def test_special_imports() -> Dict[str, Any]:
    """Test des imports spéciaux (magic, etc.)"""
    print("\n" + "="*60)
    print("PHASE 8: IMPORTS SPÉCIAUX")
    print("="*60)
    
    special_imports = [
        ("magic", "import magic"),
        ("python_multipart", "import multipart"),
    ]
    
    results = {}
    for name, import_cmd in special_imports:
        try:
            print(f"Test {name}...")
            exec(import_cmd)
            print(f"✓ {name}: OK")
            results[name] = {"status": "OK"}
        except Exception as e:
            print(f"✗ {name}: ERREUR - {str(e)}")
            results[name] = {"status": "ERROR", "error": str(e)}
            if name == "magic":
                print("  INFO: magic peut nécessiter libmagic sur Windows")
    
    return results

def test_local_module_imports() -> Dict[str, Any]:
    """Test des imports de modules locaux"""
    print("\n" + "="*60)
    print("PHASE 9: IMPORTS MODULES LOCAUX")
    print("="*60)
    
    import os
    
    local_modules = [
        ("auth", "from auth import authenticate_user, create_access_token"),
        ("database_encrypted", "from database_encrypted import get_encrypted_engine"),
        ("audit_logger", "from audit_logger import get_audit_logger, AuditEventType"),
    ]
    
    results = {}
    for name, import_cmd in local_modules:
        # Vérifier d'abord l'existence du fichier
        module_file = f"{name}.py"
        if not os.path.exists(module_file):
            print(f"✗ {name}: FICHIER MANQUANT - {module_file}")
            results[name] = {"status": "FILE_MISSING", "file": module_file}
            continue
            
        try:
            print(f"Test {name}... (fichier existe)")
            exec(import_cmd)
            print(f"✓ {name}: OK")
            results[name] = {"status": "OK"}
        except Exception as e:
            print(f"✗ {name}: ERREUR - {str(e)}")
            results[name] = {"status": "ERROR", "error": str(e)}
            traceback.print_exc()
    
    return results

def run_complete_test() -> Dict[str, Any]:
    """Lance le test complet étape par étape"""
    print("DÉBUT TEST IMPORTS ÉTAPE PAR ÉTAPE")
    print("="*80)
    
    phases = [
        ("basic", test_basic_imports),
        ("typing", test_typing_imports),
        ("scientific", test_scientific_imports),
        ("fastapi", test_fastapi_imports),
        ("validation", test_validation_imports),
        ("database", test_database_imports),
        ("crypto", test_crypto_imports),
        ("special", test_special_imports),
        ("local_modules", test_local_module_imports),
    ]
    
    results = {}
    successful_phases = []
    failed_phases = []
    
    for phase_name, test_func in phases:
        try:
            phase_results = test_func()
            results[phase_name] = phase_results
            
            # Vérifier si la phase a réussi
            phase_errors = [k for k, v in phase_results.items() if v.get("status") != "OK"]
            if phase_errors:
                failed_phases.append((phase_name, phase_errors))
            else:
                successful_phases.append(phase_name)
                
        except Exception as e:
            print(f"ERREUR CRITIQUE DANS PHASE {phase_name}: {e}")
            traceback.print_exc()
            results[phase_name] = {"CRITICAL_ERROR": str(e)}
            failed_phases.append((phase_name, ["CRITICAL_ERROR"]))
    
    # Résumé final
    print("\n" + "="*80)
    print("RÉSUMÉ FINAL")
    print("="*80)
    
    print(f"✓ Phases réussies: {', '.join(successful_phases)}")
    if failed_phases:
        print("✗ Phases avec erreurs:")
        for phase, errors in failed_phases:
            print(f"  - {phase}: {', '.join(errors)}")
    
    # Sauvegarde
    try:
        with open('test_imports_report.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Rapport détaillé sauvegardé: test_imports_report.json")
    except Exception as e:
        print(f"✗ Erreur sauvegarde: {e}")
    
    return results

if __name__ == "__main__":
    try:
        results = run_complete_test()
        print("\n" + "="*40)
        print("TEST TERMINÉ")
        print("="*40)
    except KeyboardInterrupt:
        print("\nTest interrompu par l'utilisateur")
    except Exception as e:
        print(f"Erreur critique: {e}")
        traceback.print_exc()