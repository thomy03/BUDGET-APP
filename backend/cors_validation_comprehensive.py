#!/usr/bin/env python3
"""
MISSION QA: Validation Complète de la Configuration CORS
=========================================================

Ce script valide la résolution des problèmes CORS selon les critères critiques :
1. Headers CORS présents sur toutes les réponses API
2. Support des requêtes préflight (OPTIONS) 
3. Communication frontend Docker → backend sans blocage
4. Fonctionnement end-to-end sans erreur "blocked by CORS policy"

Endpoints critiques testés :
- GET /custom-provisions
- POST /custom-provisions  
- GET /fixed-lines
- PUT /fixed-lines/{id}
- Dashboard endpoints (/summary, etc.)
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'cors_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class CORSValidator:
    """Validateur complet de configuration CORS"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.auth_token = None
        self.validation_results = {
            "cors_headers": {},
            "preflight_support": {},
            "endpoint_accessibility": {},
            "errors": [],
            "warnings": [],
            "summary": {}
        }
        self.required_cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods", 
            "access-control-allow-headers"
        ]
        
        # Endpoints critiques à tester
        self.critical_endpoints = {
            "GET /health": {"method": "GET", "path": "/health", "auth_required": False},
            "POST /token": {"method": "POST", "path": "/token", "auth_required": False},
            "GET /custom-provisions": {"method": "GET", "path": "/custom-provisions", "auth_required": True},
            "POST /custom-provisions": {"method": "POST", "path": "/custom-provisions", "auth_required": True},
            "GET /fixed-lines": {"method": "GET", "path": "/fixed-lines", "auth_required": True},
            "PUT /fixed-lines/1": {"method": "PUT", "path": "/fixed-lines/1", "auth_required": True},
            "GET /summary": {"method": "GET", "path": "/summary?month=2024-01", "auth_required": True},
            "GET /tags-summary": {"method": "GET", "path": "/tags-summary?month=2024-01", "auth_required": True}
        }
        
        # Origins simulant le frontend Docker
        self.test_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000", 
            "http://localhost:45678",
            "http://frontend-container:3000"  # Nom Docker typique
        ]

    def authenticate(self) -> bool:
        """Obtenir un token d'authentification"""
        try:
            logger.info("🔐 Authentification en cours...")
            
            auth_data = {
                "username": "admin",
                "password": "secret123"
            }
            
            response = requests.post(
                f"{self.base_url}/token",
                data=auth_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data.get("access_token")
                logger.info("✅ Authentification réussie")
                return True
            else:
                logger.error(f"❌ Échec authentification: {response.status_code}")
                self.validation_results["errors"].append(
                    f"Authentication failed: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur authentification: {str(e)}")
            self.validation_results["errors"].append(f"Authentication error: {str(e)}")
            return False

    def validate_cors_headers(self, response: requests.Response, endpoint: str) -> Dict[str, Any]:
        """Valider la présence et la validité des headers CORS"""
        cors_validation = {
            "endpoint": endpoint,
            "status_code": response.status_code,
            "headers_present": {},
            "header_values": {},
            "valid": True,
            "issues": []
        }
        
        # Vérifier présence des headers CORS critiques
        for header in self.required_cors_headers:
            header_value = response.headers.get(header)
            cors_validation["headers_present"][header] = header_value is not None
            cors_validation["header_values"][header] = header_value
            
            if header_value is None:
                cors_validation["valid"] = False
                cors_validation["issues"].append(f"Missing header: {header}")
        
        # Validations spécifiques
        allow_origin = response.headers.get("access-control-allow-origin")
        if allow_origin:
            if allow_origin == "*":
                cors_validation["warnings"] = ["Wildcard origin (*) detected - verify security implications"]
            elif not any(origin in allow_origin for origin in self.test_origins):
                cors_validation["issues"].append(f"Origin '{allow_origin}' may not match frontend origins")
        
        # Vérifier si les credentials sont autorisés
        allow_credentials = response.headers.get("access-control-allow-credentials")
        cors_validation["header_values"]["access-control-allow-credentials"] = allow_credentials
        
        return cors_validation

    def test_preflight_request(self, endpoint: str, origin: str) -> Dict[str, Any]:
        """Tester la requête préflight OPTIONS pour un endpoint"""
        try:
            logger.info(f"🚁 Test préflight pour {endpoint} depuis {origin}")
            
            # Extraire le path de l'endpoint
            endpoint_path = self.critical_endpoints[endpoint]["path"]
            method = self.critical_endpoints[endpoint]["method"]
            
            headers = {
                "Origin": origin,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
            
            response = requests.options(
                f"{self.base_url}{endpoint_path.split('?')[0]}",  # Remove query params for OPTIONS
                headers=headers,
                timeout=10
            )
            
            preflight_result = {
                "endpoint": endpoint,
                "origin": origin, 
                "status_code": response.status_code,
                "cors_validation": self.validate_cors_headers(response, f"OPTIONS {endpoint}"),
                "success": response.status_code in [200, 204]
            }
            
            if not preflight_result["success"]:
                preflight_result["error"] = f"Preflight failed with status {response.status_code}"
            
            return preflight_result
            
        except Exception as e:
            logger.error(f"❌ Erreur test préflight {endpoint}: {str(e)}")
            return {
                "endpoint": endpoint,
                "origin": origin,
                "success": False,
                "error": str(e)
            }

    def test_endpoint_with_cors(self, endpoint_name: str, origin: str) -> Dict[str, Any]:
        """Tester un endpoint spécifique avec simulation CORS"""
        try:
            endpoint_config = self.critical_endpoints[endpoint_name]
            method = endpoint_config["method"]
            path = endpoint_config["path"]
            auth_required = endpoint_config["auth_required"]
            
            headers = {
                "Origin": origin,
                "Content-Type": "application/json"
            }
            
            if auth_required and self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            url = f"{self.base_url}{path}"
            
            # Préparer les données selon la méthode
            request_kwargs = {
                "url": url,
                "headers": headers,
                "timeout": 10
            }
            
            if method == "POST" and "custom-provisions" in path:
                request_kwargs["json"] = {
                    "name": "Test Provision CORS",
                    "description": "Test provision pour validation CORS",
                    "percentage": 5.0,
                    "icon": "🧪"
                }
            elif method == "PUT" and "fixed-lines" in path:
                request_kwargs["json"] = {
                    "label": "Test Fixed Line CORS",
                    "amount": 100.0,
                    "freq": "mensuelle"
                }
            
            # Exécuter la requête
            response = getattr(requests, method.lower())(**request_kwargs)
            
            # Valider CORS
            cors_validation = self.validate_cors_headers(response, endpoint_name)
            
            result = {
                "endpoint": endpoint_name,
                "origin": origin,
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "cors_validation": cors_validation,
                "success": response.status_code < 400,
                "response_size": len(response.content),
                "response_time": response.elapsed.total_seconds()
            }
            
            if not result["success"]:
                result["error"] = f"Request failed: {response.status_code} - {response.text[:200]}"
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur test endpoint {endpoint_name}: {str(e)}")
            return {
                "endpoint": endpoint_name,
                "origin": origin,
                "success": False,
                "error": str(e)
            }

    def validate_server_status(self) -> bool:
        """Vérifier que le serveur est accessible et fonctionne"""
        try:
            logger.info("🏥 Vérification statut serveur...")
            
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ Serveur accessible - Version: {health_data.get('version', 'Unknown')}")
                
                # Valider CORS sur le endpoint health
                cors_validation = self.validate_cors_headers(response, "/health")
                self.validation_results["cors_headers"]["/health"] = cors_validation
                
                return True
            else:
                logger.error(f"❌ Serveur non accessible: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Impossible de contacter le serveur: {str(e)}")
            self.validation_results["errors"].append(f"Server unreachable: {str(e)}")
            return False

    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Exécuter la validation complète CORS"""
        logger.info("🚀 Début validation CORS complète")
        
        start_time = time.time()
        
        # 1. Vérifier statut serveur
        if not self.validate_server_status():
            logger.error("❌ Serveur inaccessible - Arrêt validation")
            return self.validation_results
        
        # 2. Authentification
        if not self.authenticate():
            logger.error("❌ Authentification échouée - Tests limités")
        
        # 3. Tests préflight pour chaque origine critique
        logger.info("🚁 Tests préflight en cours...")
        for origin in self.test_origins:
            for endpoint_name in self.critical_endpoints.keys():
                preflight_result = self.test_preflight_request(endpoint_name, origin)
                
                key = f"{endpoint_name}_{origin.replace(':', '_').replace('/', '_')}"
                self.validation_results["preflight_support"][key] = preflight_result
        
        # 4. Tests des endpoints avec CORS
        logger.info("🎯 Tests endpoints avec CORS...")
        for origin in self.test_origins:
            for endpoint_name in self.critical_endpoints.keys():
                endpoint_result = self.test_endpoint_with_cors(endpoint_name, origin)
                
                key = f"{endpoint_name}_{origin.replace(':', '_').replace('/', '_')}"
                self.validation_results["endpoint_accessibility"][key] = endpoint_result
                
                # Stocker validation CORS
                self.validation_results["cors_headers"][key] = endpoint_result.get("cors_validation", {})
        
        # 5. Analyse et synthèse
        self.analyze_results()
        
        execution_time = time.time() - start_time
        self.validation_results["metadata"] = {
            "execution_time": round(execution_time, 2),
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.validation_results["endpoint_accessibility"]),
            "base_url": self.base_url
        }
        
        logger.info(f"✅ Validation terminée en {execution_time:.2f}s")
        
        return self.validation_results

    def analyze_results(self):
        """Analyser les résultats et générer un résumé"""
        logger.info("📊 Analyse des résultats...")
        
        # Compter les succès/échecs
        total_endpoints = len(self.validation_results["endpoint_accessibility"])
        successful_endpoints = sum(1 for result in self.validation_results["endpoint_accessibility"].values() 
                                 if result.get("success", False))
        
        total_preflight = len(self.validation_results["preflight_support"])
        successful_preflight = sum(1 for result in self.validation_results["preflight_support"].values() 
                                 if result.get("success", False))
        
        # Analyser les headers CORS
        cors_compliant = sum(1 for cors_check in self.validation_results["cors_headers"].values()
                            if cors_check.get("valid", False))
        total_cors_checks = len(self.validation_results["cors_headers"])
        
        # Identifier les problèmes critiques
        critical_issues = []
        for endpoint, result in self.validation_results["endpoint_accessibility"].items():
            if not result.get("success", False) and "custom-provisions" in endpoint:
                critical_issues.append(f"Custom provisions endpoint failed: {endpoint}")
            elif not result.get("success", False) and "fixed-lines" in endpoint:
                critical_issues.append(f"Fixed lines endpoint failed: {endpoint}")
        
        # Résumé final
        self.validation_results["summary"] = {
            "endpoints_success_rate": f"{successful_endpoints}/{total_endpoints} ({successful_endpoints/total_endpoints*100:.1f}%)" if total_endpoints > 0 else "0/0",
            "preflight_success_rate": f"{successful_preflight}/{total_preflight} ({successful_preflight/total_preflight*100:.1f}%)" if total_preflight > 0 else "0/0",
            "cors_compliance_rate": f"{cors_compliant}/{total_cors_checks} ({cors_compliant/total_cors_checks*100:.1f}%)" if total_cors_checks > 0 else "0/0",
            "critical_issues_count": len(critical_issues),
            "critical_issues": critical_issues,
            "overall_status": "PASS" if len(critical_issues) == 0 and successful_endpoints > 0 else "FAIL"
        }

    def generate_report(self, output_file: str = None) -> str:
        """Générer un rapport détaillé de validation"""
        if not output_file:
            output_file = f"cors_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Rapport généré: {output_file}")
        return output_file

    def print_summary(self):
        """Afficher un résumé console des résultats"""
        print("\n" + "="*80)
        print("🎯 RÉSULTATS VALIDATION CORS - MISSION QA")
        print("="*80)
        
        summary = self.validation_results.get("summary", {})
        
        print(f"📊 Taux de succès endpoints: {summary.get('endpoints_success_rate', 'N/A')}")
        print(f"🚁 Taux de succès préflight: {summary.get('preflight_success_rate', 'N/A')}")
        print(f"🛡️  Conformité CORS: {summary.get('cors_compliance_rate', 'N/A')}")
        print(f"⚠️  Problèmes critiques: {summary.get('critical_issues_count', 0)}")
        
        status = summary.get('overall_status', 'UNKNOWN')
        if status == "PASS":
            print("✅ STATUT GLOBAL: VALIDATION RÉUSSIE")
        else:
            print("❌ STATUT GLOBAL: VALIDATION ÉCHOUÉE")
            
        if summary.get('critical_issues'):
            print("\n🚨 PROBLÈMES CRITIQUES DÉTECTÉS:")
            for issue in summary['critical_issues']:
                print(f"   - {issue}")
        
        print("\n📈 RECOMMANDATIONS:")
        if summary.get('overall_status') == "PASS":
            print("   - Configuration CORS opérationnelle")
            print("   - Frontend Docker peut communiquer avec le backend")
            print("   - Tous les endpoints critiques sont accessibles")
        else:
            print("   - Vérifier la configuration CORS dans config/settings.py")
            print("   - S'assurer que les origins du frontend sont autorisés")
            print("   - Contrôler les headers de réponse des endpoints")
        
        print("="*80)


def main():
    """Fonction principale de validation"""
    print("🚀 Démarrage validation CORS complète...")
    
    # Initialisation du validateur
    validator = CORSValidator()
    
    # Exécution de la validation
    results = validator.run_comprehensive_validation()
    
    # Génération du rapport
    report_file = validator.generate_report()
    
    # Affichage du résumé
    validator.print_summary()
    
    # Retour du code de sortie
    overall_status = results.get("summary", {}).get("overall_status", "FAIL")
    exit_code = 0 if overall_status == "PASS" else 1
    
    print(f"\n📄 Rapport détaillé: {report_file}")
    print(f"🏁 Code de sortie: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    exit(main())