# 🔧 SOLUTION PROBLÈME ESPACES WINDOWS

## ❌ **PROBLÈME IDENTIFIÉ**
Le chemin contient des espaces :
```
C:\Users\tkado\OneDrive\Documents\fichiers perso\fichier thomas et iana\budget-app-starter-v2.3
```
Windows a des difficultés avec les espaces dans les chemins des scripts.

## ✅ **SOLUTION EN 3 ÉTAPES**

### **ÉTAPE 1: Configuration initiale**
Double-cliquez sur : **`START_MANUEL.bat`**
- Configure l'environnement Python
- Installe toutes les dépendances  
- Crée les fichiers de configuration

### **ÉTAPE 2: Démarrer le backend**
Double-cliquez sur : **`start_backend.bat`**
- Lance l'API sur http://127.0.0.1:8000
- Laissez cette fenêtre OUVERTE

### **ÉTAPE 3: Démarrer le frontend** 
Double-cliquez sur : **`start_frontend.bat`**
- Lance l'interface sur http://localhost:45678  
- Laissez cette fenêtre OUVERTE

## 🎯 **ORDRE D'EXÉCUTION**

1. **`START_MANUEL.bat`** (une seule fois)
2. **`start_backend.bat`** (laisser ouvert)  
3. **`start_frontend.bat`** (laisser ouvert)
4. **Ouvrir navigateur** : http://localhost:45678
5. **Se connecter** : admin / secret

## ⚠️ **IMPORTANT**
- **NE FERMEZ PAS** les fenêtres backend et frontend
- Si erreur : redémarrer dans l'ordre 2→3→4
- **Attendre 30 secondes** entre chaque étape

## 🔍 **ALTERNATIVE SI PROBLÈME PERSISTE**

Si les espaces posent toujours problème, il faut **déplacer le dossier** :

1. **Copier** tout le dossier `budget-app-starter-v2.3` 
2. **Coller** dans `C:\budget-app\` (sans espaces)
3. **Relancer** les scripts depuis le nouveau dossier

---

**Cette approche en 3 scripts séparés évite les problèmes de chemins avec espaces.**