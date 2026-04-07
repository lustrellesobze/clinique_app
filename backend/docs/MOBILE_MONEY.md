# 📱 Documentation Mobile Money

## Vue d'ensemble

Le système de paiement Mobile Money permet d'accepter les paiements via MTN MoMo et Orange Money avec notifications WebSocket en temps réel pour les caissiers.

## Fonctionnalités

### ✅ Implémenté

1. **Initiation de paiement**
   - Support MTN MoMo et Orange Money
   - Validation des montants et factures
   - Génération d'ID de transaction unique

2. **Confirmation de paiement**
   - Callbacks simulés pour tests
   - Mise à jour automatique des factures
   - Gestion des statuts (pending, success, failed)

3. **Notifications WebSocket**
   - Notification en temps réel au caissier
   - Message de succès ou d'échec
   - Détails de la transaction inclus

4. **Suivi des transactions**
   - Consultation du statut en temps réel
   - Historique des transactions

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Caissier  │────────>│   Backend    │────────>│  Mobile     │
│   (Client)  │         │   FastAPI    │         │  Money API  │
└─────────────┘         └──────────────┘         └─────────────┘
       ↑                        │                        │
       │                        │                        │
       │                   WebSocket                Callback
       │                   Notification                  │
       │                        │                        │
       └────────────────────────┴────────────────────────┘
```

## API Endpoints

### 1. Initier un paiement

**POST** `/api/payments/mobile-money/initiate`

**Body:**
```json
{
  "facture_id": "uuid-de-la-facture",
  "montant": 50000,
  "telephone": "+237 670 00 00 01",
  "provider": "mtn_momo"  // ou "orange_money"
}
```

**Response:**
```json
{
  "transaction_id": "uuid-de-la-transaction",
  "status": "pending",
  "message": "Paiement MTN_MOMO initié. En attente de confirmation du client.",
  "montant": 50000,
  "telephone": "+237 670 00 00 01"
}
```

### 2. Vérifier le statut

**GET** `/api/payments/mobile-money/status/{transaction_id}`

**Response:**
```json
{
  "transaction_id": "uuid",
  "status": "success",
  "facture_id": "uuid",
  "montant": 50000,
  "provider": "mtn_momo",
  "created_at": "2026-04-07T14:30:00",
  "updated_at": "2026-04-07T14:30:15"
}
```

### 3. Callback MTN MoMo (Simulation)

**POST** `/api/payments/mobile-money/callback/mtn`

**Body:**
```json
{
  "transaction_id": "uuid",
  "success": true,
  "error_message": null
}
```

### 4. Callback Orange Money (Simulation)

**POST** `/api/payments/mobile-money/callback/orange`

**Body:**
```json
{
  "transaction_id": "uuid",
  "success": false,
  "error_message": "Solde insuffisant"
}
```

## Notifications WebSocket

Lorsqu'un paiement est confirmé ou échoue, une notification est automatiquement envoyée au caissier via WebSocket.

### Format de notification (Succès)

```json
{
  "type": "notification",
  "data": {
    "id": "notification-uuid",
    "type_notification": "paiement",
    "titre": "Paiement Mobile Money confirmé",
    "message": "Paiement de 50,000 FCFA confirmé via MTN_MOMO pour la facture FAC-2026-001.",
    "est_lue": false,
    "created_at": "2026-04-07T14:30:15",
    "transaction_id": "transaction-uuid",
    "facture_numero": "FAC-2026-001",
    "montant": 50000,
    "status": "success"
  }
}
```

### Format de notification (Échec)

```json
{
  "type": "notification",
  "data": {
    "id": "notification-uuid",
    "type_notification": "alerte",
    "titre": "Paiement Mobile Money échoué",
    "message": "Échec du paiement de 50,000 FCFA via MTN_MOMO. Raison: Solde insuffisant",
    "est_lue": false,
    "created_at": "2026-04-07T14:30:15",
    "transaction_id": "transaction-uuid",
    "facture_numero": "FAC-2026-001",
    "montant": 50000,
    "status": "failed"
  }
}
```

## Flux de paiement

### Scénario de succès

1. **Caissier initie le paiement**
   ```
   POST /api/payments/mobile-money/initiate
   ```

2. **Client reçoit notification sur son téléphone**
   - Demande de confirmation du paiement
   - Saisie du code PIN

3. **Client confirme le paiement**
   - MTN/Orange traite le paiement

4. **Callback reçu par le backend**
   ```
   POST /api/payments/mobile-money/callback/mtn
   ```

5. **Backend met à jour la facture**
   - Montant réglé augmenté
   - Statut facture mis à jour

6. **Notification WebSocket envoyée au caissier**
   - Message de confirmation
   - Détails de la transaction

### Scénario d'échec

1-3. Mêmes étapes que le succès

4. **Client annule ou échec du paiement**
   - Solde insuffisant
   - Code PIN incorrect
   - Timeout

5. **Callback d'échec reçu**
   ```
   POST /api/payments/mobile-money/callback/mtn
   {
     "success": false,
     "error_message": "Solde insuffisant"
   }
   ```

6. **Notification d'échec envoyée au caissier**
   - Message d'erreur
   - Raison de l'échec

## Tests

### Script de test automatique

```bash
cd clinique_app/backend
venv\Scripts\activate
python scripts/test_mobile_money.py
```

Ce script teste :
- ✅ Initiation de paiement MTN MoMo
- ✅ Confirmation de paiement réussi
- ✅ Mise à jour de la facture
- ✅ Initiation de paiement Orange Money
- ✅ Simulation d'échec de paiement
- ✅ Notifications WebSocket

### Test manuel via Swagger

1. Accéder à `http://localhost:8000/docs`
2. S'authentifier avec un compte caissier
3. Tester les endpoints `/payments/mobile-money/*`

## Statuts des transactions

| Statut | Description |
|--------|-------------|
| `pending` | Paiement initié, en attente de confirmation |
| `success` | Paiement confirmé avec succès |
| `failed` | Paiement échoué |
| `cancelled` | Paiement annulé par le client |

## Fournisseurs supportés

| Fournisseur | Code | Préfixe téléphone |
|-------------|------|-------------------|
| MTN MoMo | `mtn_momo` | +237 67X, 65X |
| Orange Money | `orange_money` | +237 69X, 65X |

## Sécurité

### En production

⚠️ **Important**: Le code actuel est une simulation pour tests.

Pour la production, il faut :

1. **Intégrer les vraies API**
   - MTN MoMo API
   - Orange Money API

2. **Sécuriser les callbacks**
   - Vérification des signatures
   - Validation des IPs sources
   - Tokens d'authentification

3. **Stocker les transactions en base**
   - Créer une table `mobile_money_transactions`
   - Logger tous les événements
   - Audit trail complet

4. **Gérer les erreurs**
   - Retry automatique
   - Timeouts configurables
   - Alertes administrateur

## Configuration

### Variables d'environnement (Production)

```env
# MTN MoMo
MTN_MOMO_API_KEY=your_api_key
MTN_MOMO_API_SECRET=your_api_secret
MTN_MOMO_CALLBACK_URL=https://your-domain.com/api/payments/mobile-money/callback/mtn

# Orange Money
ORANGE_MONEY_API_KEY=your_api_key
ORANGE_MONEY_API_SECRET=your_api_secret
ORANGE_MONEY_CALLBACK_URL=https://your-domain.com/api/payments/mobile-money/callback/orange
```

## Dépannage

### Problème: Notification WebSocket non reçue

**Solution:**
1. Vérifier que le WebSocket est connecté
2. Vérifier le token JWT
3. Vérifier les logs du serveur

### Problème: Transaction bloquée en "pending"

**Solution:**
1. Vérifier les logs de callback
2. Simuler manuellement le callback
3. Contacter le support du fournisseur

### Problème: Facture non mise à jour

**Solution:**
1. Vérifier que le callback a été reçu
2. Vérifier les logs de la base de données
3. Vérifier les permissions du caissier

## Support

Pour toute question ou problème :
- Consulter les logs : `clinique_app/backend/logs/`
- Vérifier la documentation API : `http://localhost:8000/docs`
- Contacter l'équipe technique
