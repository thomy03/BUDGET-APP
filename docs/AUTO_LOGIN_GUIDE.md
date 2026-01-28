# ✅ Guide Auto-Login - Budget Famille v2.3 (06/11/2025)

## 🎯 Objectif

Permettre à l'utilisateur de lancer l'application et d'accéder directement au Dashboard **sans avoir à saisir d'identifiant et mot de passe**.

## 🚀 Solution Implémentée

### 1. Script de Lancement Rapide

**Fichier** : `LANCER_APP.bat` (à la racine du projet)

Double-cliquez sur ce fichier pour démarrer automatiquement :
- ✅ Backend FastAPI (port 8000)
- ✅ Frontend Next.js (port 3000)
- ✅ Ouverture automatique du navigateur

```batch
@echo off
title Budget Famille - Lancement

echo ========================================
echo   BUDGET FAMILLE v2.3
echo   Demarrage de l'application...
echo ========================================

# Vérifie Python et Node.js
# Démarre backend
# Démarre frontend
# Ouvre http://localhost:3000
```

### 2. Configuration Auto-Login

**Fichier** : `frontend/.env.local`

Ajoutez ces variables d'environnement :

```env
# ===================================================================
# MODE AUTO-LOGIN (désactiver l'authentification)
# ===================================================================
# Mettre à 'true' pour se connecter automatiquement sans login/password
# Mettre à 'false' pour activer l'authentification normale
NEXT_PUBLIC_AUTO_LOGIN=true
NEXT_PUBLIC_DEFAULT_USER=admin
NEXT_PUBLIC_DEFAULT_PASSWORD=secret
```

### 3. Modifications du Code

**Fichier** : `frontend/lib/auth.ts`

#### Ligne 54 : Fonction `initializeAuth()` modifiée

```typescript
private async initializeAuth() {
  if (typeof window !== "undefined") {
    try {
      // ✅ Vérifier si le mode auto-login est activé
      const autoLogin = process.env.NEXT_PUBLIC_AUTO_LOGIN === "true";
      const defaultUser = process.env.NEXT_PUBLIC_DEFAULT_USER;
      const defaultPassword = process.env.NEXT_PUBLIC_DEFAULT_PASSWORD;

      const token = localStorage.getItem("auth_token");
      const tokenType = localStorage.getItem("token_type");
      const user = localStorage.getItem("username");

      if (token && tokenType && user) {
        // Vérifier si le token n'est pas expiré
        if (!this.isTokenExpired(token)) {
          // Restaurer la session existante
          const authHeader = `${tokenType} ${token}`;
          api.defaults.headers.common["Authorization"] = authHeader;

          this.updateAuthState({
            isAuthenticated: true,
            token,
            user,
            loading: false,
          });
        } else {
          // Token expiré, nettoyer
          console.log("🔑 Token expired on initialization");
          this.clearAuthData();

          // ✅ Si auto-login activé, se reconnecter automatiquement
          if (autoLogin && defaultUser && defaultPassword) {
            console.log("🔐 Auto-login activé, reconnexion automatique...");
            await this.login(defaultUser, defaultPassword);
          }
        }
      } else if (autoLogin && defaultUser && defaultPassword) {
        // ✅ Pas de token existant mais auto-login activé
        console.log("🔐 Auto-login activé, connexion automatique...");
        await this.login(defaultUser, defaultPassword);
      } else {
        this.updateAuthState({ loading: false });
      }
    } catch (error) {
      console.error("Erreur initialisation auth:", error);
      this.clearAuthData();
    }
  }
}
```

**Fichier** : `frontend/app/page.tsx` (déjà correct)

```typescript
export default function HomePage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading) {
      if (isAuthenticated) {
        // ✅ Si authentifié, redirige vers le dashboard
        router.push("/dashboard");
      } else {
        // Si non authentifié, redirige vers la landing page
        router.push("/landing");
      }
    }
  }, [isAuthenticated, authLoading, router]);

  // Affichage du loader pendant la redirection
  return <div>Chargement...</div>;
}
```

## 📋 Comment Utiliser

### Méthode 1 : Double-clic sur le script

1. **Ouvrir le dossier du projet** : `budget-app-starter-v2.3`
2. **Double-cliquer sur** : `LANCER_APP.bat`
3. **Attendre** :
   - Backend démarre (5 secondes)
   - Frontend démarre (10 secondes)
   - Navigateur s'ouvre automatiquement
4. **Résultat** : Vous êtes directement sur le Dashboard, connecté en tant qu'admin

### Méthode 2 : Lancement manuel

```bash
# Terminal 1 - Backend
cd backend
python app.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Puis ouvrir http://localhost:3000

## 🔄 Fonctionnement

### Scénario 1 : Première visite
1. Utilisateur ouvre http://localhost:3000
2. `page.tsx` charge et vérifie l'authentification
3. `auth.ts` détecte `NEXT_PUBLIC_AUTO_LOGIN=true`
4. Auto-login appelle `login("admin", "secret")`
5. Token JWT reçu et stocké dans `localStorage`
6. `page.tsx` détecte `isAuthenticated=true`
7. Redirection automatique vers `/dashboard`

### Scénario 2 : Visites suivantes
1. Utilisateur ouvre http://localhost:3000
2. `auth.ts` trouve un token valide dans `localStorage`
3. Token pas expiré → Session restaurée
4. `page.tsx` redirige vers `/dashboard`
5. **Aucun appel réseau, redirection instantanée**

### Scénario 3 : Token expiré
1. Utilisateur ouvre http://localhost:3000
2. `auth.ts` trouve un token mais il est expiré
3. Mode auto-login activé → Reconnexion automatique
4. Nouveau token obtenu
5. Redirection vers `/dashboard`

## ⚙️ Configuration

### Activer l'auto-login

Dans `frontend/.env.local` :
```env
NEXT_PUBLIC_AUTO_LOGIN=true
```

### Désactiver l'auto-login (mode normal)

Dans `frontend/.env.local` :
```env
NEXT_PUBLIC_AUTO_LOGIN=false
```

**Résultat** : L'utilisateur devra saisir admin/secret sur la page `/login`

### Changer les identifiants par défaut

Dans `frontend/.env.local` :
```env
NEXT_PUBLIC_DEFAULT_USER=mon_utilisateur
NEXT_PUBLIC_DEFAULT_PASSWORD=mon_mot_de_passe
```

⚠️ **Important** : Ces identifiants doivent exister dans le backend (`backend/auth.py`)

## 🔒 Sécurité

### ⚠️ ATTENTION : Usage Personnel Uniquement

Le mode auto-login est conçu pour un **usage personnel sur un PC privé**.

**NE PAS UTILISER** en production publique car :
- Les identifiants sont en clair dans `.env.local`
- Pas de protection par mot de passe
- N'importe qui accédant au PC peut voir les données

### Recommandations

1. **PC Personnel** : OK pour usage familial
2. **Partage de PC** : Désactiver auto-login (`NEXT_PUBLIC_AUTO_LOGIN=false`)
3. **Déploiement Internet** :
   - **JAMAIS** avec auto-login activé
   - Utiliser authentification normale
   - Ajouter 2FA (Two-Factor Authentication)
   - Variables d'environnement sécurisées (pas dans Git)

### Sécuriser `.env.local`

Le fichier `.env.local` est déjà dans `.gitignore` :

```gitignore
# Fichiers d'environnement local
.env.local
.env.development.local
.env.test.local
.env.production.local
```

**NE JAMAIS** commiter `.env.local` dans Git !

## 🧪 Tests

### Test 1 : Auto-login activé

1. Vider le `localStorage` du navigateur (F12 → Application → Local Storage → Clear)
2. Fermer et rouvrir le navigateur
3. Aller sur http://localhost:3000
4. **Résultat attendu** : Redirection automatique vers `/dashboard` sans page de login

### Test 2 : Auto-login désactivé

1. Modifier `.env.local` : `NEXT_PUBLIC_AUTO_LOGIN=false`
2. Redémarrer le frontend : `npm run dev`
3. Vider le `localStorage`
4. Aller sur http://localhost:3000
5. **Résultat attendu** : Page `/login` s'affiche

### Test 3 : Token expiré avec auto-login

1. Modifier le token dans `localStorage` pour le rendre invalide
2. Rafraîchir la page
3. **Résultat attendu** : Reconnexion automatique puis redirection vers `/dashboard`

### Test 4 : Script de lancement

1. Double-cliquer sur `LANCER_APP.bat`
2. Attendre 15 secondes
3. **Résultat attendu** :
   - Backend running sur http://localhost:8000
   - Frontend running sur http://localhost:3000
   - Navigateur ouvert sur Dashboard

## 🐛 Dépannage

### Problème : Page login s'affiche malgré auto-login

**Causes possibles** :
1. `.env.local` mal configuré
2. Frontend pas redémarré après changement `.env.local`
3. Erreur réseau (backend pas accessible)

**Solutions** :
```bash
# Vérifier .env.local
cat frontend/.env.local | grep AUTO_LOGIN

# Redémarrer frontend
cd frontend
rm -rf .next
npm run dev
```

### Problème : Token expiré à chaque fois

**Cause** : Les tokens JWT expirent après 7 jours

**Solution** : Le mode auto-login se reconnecte automatiquement

**Vérifier dans la console** :
```
🔑 Token expired on initialization
🔐 Auto-login activé, reconnexion automatique...
```

### Problème : Backend pas accessible

**Erreur** : `Erreur de connexion inconnue`

**Solutions** :
```bash
# Vérifier que le backend tourne
curl http://localhost:8000/health

# Relancer le backend
cd backend
python app.py
```

## 📝 Fichiers Modifiés

1. ✅ `LANCER_APP.bat` - Script de lancement (créé)
2. ✅ `frontend/.env.local` - Configuration auto-login (modifié)
3. ✅ `frontend/lib/auth.ts` - Logique auto-login (lignes 54-109)
4. ✅ `frontend/app/page.tsx` - Redirection automatique (déjà correct)

## 🎉 Résultat

**Expérience utilisateur** :
1. Double-clic sur `LANCER_APP.bat`
2. Attendre 15 secondes
3. Application ouverte sur le Dashboard
4. **Aucun identifiant à saisir** ✅

**Maintenance** :
- Pas besoin de se souvenir des identifiants
- Pas de page login à chaque visite
- Reconnexion automatique si token expiré

---

**Version** : 2.3.13
**Date** : 06/11/2025
**Fichiers modifiés** :
- `LANCER_APP.bat` (créé)
- `frontend/.env.local` (modifié)
- `frontend/lib/auth.ts` (lignes 54-109)
- `docs/AUTO_LOGIN_GUIDE.md` (créé)

**Statut** : ✅ Auto-login implémenté et fonctionnel
