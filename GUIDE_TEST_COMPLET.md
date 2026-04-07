# 🧪 Guide de Test Complet - Application Clinique

## 📋 Table des matières

1. [Préparation](#préparation)
2. [Test Backend](#test-backend)
3. [Test Frontend](#test-frontend)
4. [Test Notifications WebSocket](#test-notifications-websocket)
5. [Test Mobile Money](#test-mobile-money)
6. [Test PDF](#test-pdf)
7. [Dépannage](#dépannage)

---

## 🚀 Préparation

### Étape 1 : Vérifier la base de données

```cmd
# Ouvrir WAMP/XAMPP et démarrer MySQL
# Vérifier que la base "clinique_db" existe
```

### Étape 2 : Créer les données de test

```cmd
cd clinique_app\backend
venv\Scripts\activate
python scripts\seed_all_data.py
```

**Résultat attendu :**
```
✅ 7 utilisateurs créés
✅ 3 assurances créées
✅ 5 patients créés
✅ 12 factures créées
✅ 33 notifications créées
```

**Identifiants créés :**
- Admin: `admin@demo.cm` / `demo123`
- Médecin: `medecin@demo.cm` / `demo123`
- Infirmier: `infirmier@demo.cm` / `demo123`
- Caissier: `caissier@demo.cm` / `demo123`
- Labo: `labo@demo.cm` / `demo123`
- Imagerie: `imagerie@demo.cm` / `demo123`
- Assurance: `assurance@demo.cm` / `demo123`

---

## 🔧 Test Backend

### Étape 1 : Démarrer le serveur backend

```cmd
cd clinique_app\backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Résultat attendu :**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Étape 2 : Tester l'API avec Swagger

1. Ouvrir le navigateur : `http://127.0.0.1:8000/docs`

2. **Tester l'authentification :**
   - Cliquer sur `POST /api/auth/login`
   - Cliquer sur "Try it out"
   - Entrer :
     ```json
     {
       "email": "caissier@demo.cm",
       "password": "demo123"
     }
     ```
   - Cliquer "Execute"
   - **Résultat attendu :** Token JWT retourné

3. **S'authentifier dans Swagger :**
   - Cliquer sur le bouton "Authorize" en haut à droite
   - Entrer : `Bearer <votre_token>`
   - Cliquer "Authorize"

4. **Tester les notifications :**
   - Aller à `GET /api/notifications/`
   - Cliquer "Try it out" → "Execute"
   - **Résultat attendu :** Liste de notifications

5. **Tester le compteur de notifications :**
   - Aller à `GET /api/notifications/unread-count`
   - Cliquer "Try it out" → "Execute"
   - **Résultat attendu :** `{"count": 5}` (ou autre nombre)

---

## 🌐 Test Frontend

### Étape 1 : Démarrer le serveur frontend

**Ouvrir un NOUVEAU terminal :**

```cmd
cd clinique_app\frontend
npm start
```

**Résultat attendu :**
```
Application bundle generation complete.
Local:   http://localhost:4200/
```

### Étape 2 : Tester la connexion

1. Ouvrir le navigateur : `http://localhost:4200`

2. **Page de connexion :**
   - Cliquer sur "Se connecter"
   - Entrer : `caissier@demo.cm` / `demo123`
   - Cliquer "Se connecter"
   - **Résultat attendu :** Redirection vers la page appropriée

3. **Tester les différents rôles :**

   | Rôle | Email | Redirection |
   |------|-------|-------------|
   | Infirmier | `infirmier@demo.cm` | `/accueil` |
   | Médecin | `medecin@demo.cm` | `/dashboard` |
   | Caissier | `caissier@demo.cm` | `/dashboard` |
   | Labo | `labo@demo.cm` | `/laboratoire` |
   | Imagerie | `imagerie@demo.cm` | `/imagerie` |
   | Assurance | `assurance@demo.cm` | `/assurances` |

4. **Vérifier le header :**
   - ✅ Logo "Clinique Espoir"
   - ✅ Nom et rôle de l'utilisateur
   - ✅ Bouton "Tableau de bord"
   - ✅ Bouton "Déconnexion"

---

## 🔔 Test Notifications WebSocket

### Méthode 1 : Via Script Python (Recommandé)

**Terminal 1 - Backend en cours d'exécution**

**Terminal 2 - Test des notifications :**

```cmd
cd clinique_app\backend
venv\Scripts\activate
python scripts\test_mobile_money.py
```

**Résultat attendu :**
```
✅ Paiement initié
⏳ En attente de confirmation...
🎉 PAIEMENT CONFIRMÉ!
📝 Note: Les notifications WebSocket ont été envoyées
```

### Méthode 2 : Via l'interface Swagger

1. **Créer une notification manuellement :**
   - Aller à `POST /api/notifications/`
   - Body :
     ```json
     {
       "user_id": "<id_du_caissier>",
       "type_notification": "paiement",
       "titre": "Test notification",
       "message": "Ceci est un test"
     }
     ```
   - Cliquer "Execute"

2. **Vérifier la notification :**
   - Aller à `GET /api/notifications/`
   - **Résultat attendu :** Nouvelle notification dans la liste

### Méthode 3 : Via WebSocket Client (Avancé)

**Utiliser un outil comme Postman ou un client WebSocket :**

1. Connexion WebSocket :
   ```
   ws://127.0.0.1:8000/api/ws/notifications?token=<votre_jwt_token>
   ```

2. Envoyer un ping :
   ```
   ping
   ```

3. **Résultat attendu :** Réponse `pong`

4. Dans un autre terminal, créer une notification via l'API

5. **Résultat attendu :** Message WebSocket reçu en temps réel

---

## 💰 Test Mobile Money

### Test Automatique (Recommandé)

```cmd
cd clinique_app\backend
venv\Scripts\activate
python scripts\test_mobile_money.py
```

**Ce script teste :**
- ✅ Initiation paiement MTN MoMo
- ✅ Confirmation de paiement
- ✅ Mise à jour de la facture
- ✅ Notification WebSocket au caissier
- ✅ Test d'échec de paiement Orange Money

### Test Manuel via Swagger

1. **S'authentifier en tant que caissier**

2. **Initier un paiement :**
   - Aller à `POST /api/payments/mobile-money/initiate`
   - Body :
     ```json
     {
       "facture_id": "<id_d_une_facture>",
       "montant": 50000,
       "telephone": "+237 670 00 00 01",
       "provider": "mtn_momo"
     }
     ```
   - Cliquer "Execute"
   - **Noter le `transaction_id` retourné**

3. **Vérifier le statut :**
   - Aller à `GET /api/payments/mobile-money/status/{transaction_id}`
   - Entrer le transaction_id
   - **Résultat attendu :** `"status": "pending"`

4. **Simuler la confirmation :**
   - Aller à `POST /api/payments/mobile-money/callback/mtn`
   - Body :
     ```json
     {
       "transaction_id": "<votre_transaction_id>",
       "success": true,
       "error_message": null
     }
     ```
   - Cliquer "Execute"
   - **Résultat attendu :** `"status": "success"`

5. **Vérifier la notification :**
   - Aller à `GET /api/notifications/`
   - **Résultat attendu :** Nouvelle notification de paiement confirmé

6. **Vérifier la facture :**
   - Aller à `GET /api/invoices/{facture_id}` (si endpoint existe)
   - **Résultat attendu :** `montant_regle` mis à jour

---

## 📄 Test PDF

### Test 1 : Télécharger une facture PDF

1. **Via Swagger :**
   - S'authentifier
   - Aller à `GET /api/invoices/{facture_id}/pdf`
   - Entrer un ID de facture (récupérer depuis la base ou via API)
   - Cliquer "Execute"
   - Cliquer sur "Download file"
   - **Résultat attendu :** PDF téléchargé avec :
     - En-tête "CLINIQUE MÉDICALE"
     - Informations patient
     - Détails de la facture
     - Totaux

2. **Via URL directe :**
   ```
   http://127.0.0.1:8000/api/invoices/<facture_id>/pdf
   ```
   - Ouvrir dans le navigateur
   - **Résultat attendu :** PDF affiché ou téléchargé

### Test 2 : Télécharger une ordonnance PDF

1. **Via Swagger :**
   - Aller à `GET /api/prescriptions/{prescription_id}/pdf`
   - Entrer un ID d'ordonnance
   - Cliquer "Execute"
   - **Résultat attendu :** PDF d'ordonnance avec médicaments

---

## 🔍 Test des Modules

### Test Module Laboratoire

1. **Se connecter avec :** `labo@demo.cm` / `demo123`

2. **Vérifier la page :**
   - URL : `http://localhost:4200/laboratoire`
   - ✅ Header avec déconnexion
   - ✅ Titre "Laboratoire"
   - ✅ Liste des examens en attente (si données existent)

3. **Via API :**
   - `GET /api/laboratory/pending`
   - **Résultat attendu :** Liste des prescriptions labo

### Test Module Imagerie

1. **Se connecter avec :** `imagerie@demo.cm` / `demo123`

2. **Vérifier la page :**
   - URL : `http://localhost:4200/imagerie`
   - ✅ Header avec déconnexion
   - ✅ Titre "Imagerie"
   - ✅ Liste des examens en attente

3. **Via API :**
   - `GET /api/imaging/pending`
   - **Résultat attendu :** Liste des prescriptions imagerie

### Test Module Hospitalisation

1. **Se connecter avec :** `admin@demo.cm` / `demo123`

2. **Vérifier la page :**
   - URL : `http://localhost:4200/hospitalisation`
   - ✅ Formulaire d'admission
   - ✅ Liste des hospitalisations actives

3. **Via API :**
   - `GET /api/hospitalization/rooms` - Liste des chambres
   - `GET /api/hospitalization/active` - Hospitalisations en cours
   - `POST /api/hospitalization/admissions` - Admettre un patient

### Test Module Assurances

1. **Se connecter avec :** `assurance@demo.cm` / `demo123`

2. **Vérifier la page :**
   - URL : `http://localhost:4200/assurances`
   - ✅ Liste des créances d'assurance
   - ✅ Montants et statuts

3. **Via API :**
   - `GET /api/insurance/claims` (si endpoint existe)

---

## 🐛 Dépannage

### Problème : Backend ne démarre pas

**Erreur :** `ModuleNotFoundError`

**Solution :**
```cmd
cd clinique_app\backend
venv\Scripts\activate
pip install -r requirements.txt
```

### Problème : Frontend ne démarre pas

**Erreur :** `npm ERR!`

**Solution :**
```cmd
cd clinique_app\frontend
npm install
npm start
```

### Problème : Connexion échoue

**Erreur :** "Invalid credentials"

**Solution :**
1. Vérifier que le seeder a été exécuté
2. Vérifier l'email et le mot de passe
3. Vérifier les logs backend

### Problème : Notifications ne s'affichent pas

**Solution :**
1. Vérifier que le backend est démarré
2. Vérifier la connexion WebSocket dans les logs
3. Tester via Swagger d'abord

### Problème : PDF ne se génère pas

**Erreur :** "Facture non trouvée"

**Solution :**
1. Vérifier que l'ID de facture existe
2. Vérifier les permissions de l'utilisateur
3. Vérifier les logs backend

### Problème : Base de données vide

**Solution :**
```cmd
cd clinique_app\backend
venv\Scripts\activate
python scripts\seed_all_data.py
```

---

## ✅ Checklist de Test Complète

### Backend
- [ ] Serveur démarre sans erreur
- [ ] Swagger accessible sur http://127.0.0.1:8000/docs
- [ ] Authentification fonctionne
- [ ] Endpoints notifications fonctionnent
- [ ] Endpoints Mobile Money fonctionnent
- [ ] PDF se génèrent correctement

### Frontend
- [ ] Serveur démarre sans erreur
- [ ] Page de connexion accessible
- [ ] Connexion réussie pour tous les rôles
- [ ] Headers affichés sur toutes les pages
- [ ] Navigation fonctionne
- [ ] Déconnexion fonctionne

### Notifications
- [ ] Notifications créées en base
- [ ] Compteur de notifications correct
- [ ] Marquage comme lu fonctionne
- [ ] WebSocket se connecte
- [ ] Notifications reçues en temps réel

### Mobile Money
- [ ] Initiation de paiement fonctionne
- [ ] Statut transaction correct
- [ ] Confirmation met à jour la facture
- [ ] Notification envoyée au caissier
- [ ] Échec de paiement géré correctement

### PDF
- [ ] Facture PDF se génère
- [ ] Ordonnance PDF se génère
- [ ] Contenu correct et formaté
- [ ] Téléchargement fonctionne

---

## 🎯 Scénario de Test Complet (End-to-End)

### Scénario : Paiement Mobile Money avec notification

1. **Préparation :**
   ```cmd
   # Terminal 1 - Backend
   cd clinique_app\backend
   venv\Scripts\activate
   uvicorn app.main:app --reload
   
   # Terminal 2 - Frontend
   cd clinique_app\frontend
   npm start
   ```

2. **Connexion :**
   - Ouvrir `http://localhost:4200`
   - Se connecter avec `caissier@demo.cm` / `demo123`

3. **Initier un paiement (via Swagger) :**
   - Ouvrir `http://127.0.0.1:8000/docs`
   - S'authentifier
   - POST `/api/payments/mobile-money/initiate`
   - Noter le `transaction_id`

4. **Confirmer le paiement :**
   - POST `/api/payments/mobile-money/callback/mtn`
   - Avec le `transaction_id`

5. **Vérifier la notification :**
   - GET `/api/notifications/`
   - Voir la nouvelle notification de paiement

6. **Vérifier la facture :**
   - Vérifier que `montant_regle` a été mis à jour

**✅ Test réussi si :**
- Paiement initié
- Confirmation reçue
- Facture mise à jour
- Notification créée
- WebSocket envoyé (visible dans les logs)

---

## 📞 Support

Si tu rencontres des problèmes :

1. **Vérifier les logs :**
   - Backend : Terminal où uvicorn tourne
   - Frontend : Terminal où npm start tourne
   - Base de données : Logs MySQL/MariaDB

2. **Vérifier les ports :**
   - Backend : 8000
   - Frontend : 4200
   - MySQL : 3306

3. **Redémarrer les services :**
   ```cmd
   # Arrêter avec Ctrl+C
   # Redémarrer les commandes
   ```

Bon test ! 🚀
