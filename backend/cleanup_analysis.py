#!/usr/bin/env python3
"""
Analyse rapide des fichiers redondants pour nettoyage manuel
Génère un rapport des fichiers qui peuvent être nettoyés
"""

import os
from pathlib import Path
from collections import defaultdict
import json

def analyze_files():
    """Analyse les fichiers du projet"""
    base_path = Path(".")
    all_files = list(base_path.glob("*"))
    
    analysis = {
        'apps': [],
        'requirements': [],
        'scripts': [],
        'windows_files': [],
        'tests': [],
        'docs': [],
        'configs': [],
        'backups': [],
        'others': []
    }
    
    for file_path in all_files:
        if file_path.is_file():
            filename = file_path.name
            
            # Applications
            if filename.startswith('app') and filename.endswith('.py'):
                analysis['apps'].append({
                    'name': filename,
                    'size': file_path.stat().st_size,
                    'is_main': filename == 'app.py'
                })
            
            # Requirements
            elif filename.startswith('requirements') and filename.endswith('.txt'):
                analysis['requirements'].append({
                    'name': filename,
                    'size': file_path.stat().st_size,
                    'is_main': filename == 'requirements.txt'
                })
            
            # Scripts de démarrage
            elif filename.startswith('start') and filename.endswith('.py'):
                analysis['scripts'].append({
                    'name': filename,
                    'size': file_path.stat().st_size
                })
            
            # Fichiers Windows
            elif any(keyword in filename.lower() for keyword in ['windows', '.ps1', '.bat']):
                analysis['windows_files'].append({
                    'name': filename,
                    'size': file_path.stat().st_size
                })
            
            # Tests
            elif filename.startswith('test') and filename.endswith('.py'):
                analysis['tests'].append({
                    'name': filename,
                    'size': file_path.stat().st_size
                })
            
            # Documentation
            elif filename.endswith('.md'):
                analysis['docs'].append({
                    'name': filename,
                    'size': file_path.stat().st_size
                })
            
            # Configurations
            elif filename.endswith('.json'):
                analysis['configs'].append({
                    'name': filename,
                    'size': file_path.stat().st_size
                })
            
            # Backups
            elif 'backup' in filename.lower():
                analysis['backups'].append({
                    'name': filename,
                    'size': file_path.stat().st_size
                })
    
    return analysis

def generate_cleanup_report():
    """Génère un rapport de nettoyage"""
    analysis = analyze_files()
    
    print("🧹 ANALYSE DE NETTOYAGE BUDGET FAMILLE v2.3")
    print("=" * 60)
    
    total_size = 0
    cleanup_recommendations = []
    
    # Applications redondantes
    apps = analysis['apps']
    main_app = next((a for a in apps if a['is_main']), None)
    redundant_apps = [a for a in apps if not a['is_main']]
    
    if redundant_apps:
        print(f"\n📱 APPLICATIONS ({len(apps)} total)")
        print(f"   ✅ Principal: {main_app['name'] if main_app else 'AUCUN!'}")
        print("   🗑️  Redondantes:")
        for app in redundant_apps:
            size_kb = app['size'] / 1024
            print(f"      - {app['name']} ({size_kb:.1f} KB)")
            total_size += app['size']
            cleanup_recommendations.append(f"rm {app['name']}")
    
    # Requirements redondants
    reqs = analysis['requirements']
    main_req = next((r for r in reqs if r['is_main']), None)
    redundant_reqs = [r for r in reqs if not r['is_main']]
    
    if redundant_reqs:
        print(f"\n📦 REQUIREMENTS ({len(reqs)} total)")
        print(f"   ✅ Principal: {main_req['name'] if main_req else 'AUCUN!'}")
        print("   🗑️  Redondants:")
        for req in redundant_reqs:
            size_kb = req['size'] / 1024
            print(f"      - {req['name']} ({size_kb:.1f} KB)")
            total_size += req['size']
            cleanup_recommendations.append(f"rm {req['name']}")
    
    # Scripts de démarrage
    scripts = analysis['scripts']
    if scripts:
        print(f"\n🚀 SCRIPTS DE DÉMARRAGE ({len(scripts)} total)")
        print("   🗑️  Tous redondants (nouveau start.py à créer):")
        for script in scripts:
            size_kb = script['size'] / 1024
            print(f"      - {script['name']} ({size_kb:.1f} KB)")
            total_size += script['size']
            cleanup_recommendations.append(f"rm {script['name']}")
    
    # Fichiers Windows
    windows_files = analysis['windows_files']
    if windows_files:
        print(f"\n🪟 FICHIERS WINDOWS ({len(windows_files)} total)")
        print("   🗑️  Non nécessaires pour Ubuntu:")
        for wf in windows_files:
            size_kb = wf['size'] / 1024
            print(f"      - {wf['name']} ({size_kb:.1f} KB)")
            total_size += wf['size']
            cleanup_recommendations.append(f"rm {wf['name']}")
    
    # Backups DB
    backups = analysis['backups']
    if backups:
        print(f"\n💾 BACKUPS DB ({len(backups)} total)")
        print("   🗂️  À organiser avec organize_db_backups.py")
        backup_size = sum(b['size'] for b in backups)
        print(f"      Total: {backup_size / (1024*1024):.1f} MB")
    
    # Documentation Windows
    docs = analysis['docs']
    windows_docs = [d for d in docs if 'windows' in d['name'].lower()]
    if windows_docs:
        print(f"\n📄 DOCUMENTATION WINDOWS ({len(windows_docs)} total)")
        print("   🗑️  Non nécessaire pour Ubuntu:")
        for doc in windows_docs:
            size_kb = doc['size'] / 1024
            print(f"      - {doc['name']} ({size_kb:.1f} KB)")
            total_size += doc['size']
            cleanup_recommendations.append(f"rm {doc['name']}")
    
    # Tests redondants
    tests = analysis['tests']
    redundant_test_patterns = ['_simple', '_complete', '_windows', '_critical', '_minimal']
    redundant_tests = [t for t in tests if any(pattern in t['name'] for pattern in redundant_test_patterns)]
    
    if redundant_tests:
        print(f"\n🧪 TESTS REDONDANTS ({len(redundant_tests)}/{len(tests)} total)")
        print("   🗑️  Tests obsolètes/redondants:")
        for test in redundant_tests:
            size_kb = test['size'] / 1024
            print(f"      - {test['name']} ({size_kb:.1f} KB)")
            total_size += test['size']
            cleanup_recommendations.append(f"rm {test['name']}")
    
    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DU NETTOYAGE")
    print("="*60)
    print(f"💾 Espace récupérable: {total_size / (1024*1024):.1f} MB")
    print(f"🗑️  Fichiers à supprimer: {len(cleanup_recommendations)}")
    
    if cleanup_recommendations:
        print("\n💡 COMMANDES DE NETTOYAGE RECOMMANDÉES:")
        print("   # Créer un backup avant nettoyage")
        print("   mkdir -p cleanup_backup")
        for cmd in cleanup_recommendations[:10]:  # Limiter l'affichage
            print(f"   {cmd}")
        
        if len(cleanup_recommendations) > 10:
            print(f"   # ... et {len(cleanup_recommendations) - 10} autres fichiers")
        
        print("\n🚀 ALTERNATIVE: Utilisez le script de migration")
        print("   python migrate_to_consolidated.py  # Simulation")
        print("   python migrate_to_consolidated.py --execute  # Exécution")
    
    return {
        'total_size_bytes': total_size,
        'files_to_cleanup': len(cleanup_recommendations),
        'commands': cleanup_recommendations,
        'analysis': analysis
    }

if __name__ == "__main__":
    report = generate_cleanup_report()
    
    # Sauvegarder le rapport
    with open('cleanup_analysis.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📋 Rapport détaillé sauvegardé: cleanup_analysis.json")