# Configuration du CRON pour Facturation Journalière

## Description
Le script `cron_hospitalization.py` génère automatiquement les factures quotidiennes pour tous les séjours d'hospitalisation en cours.

## Fonctionnement
- **Fréquence**: Tous les jours à 00:01
- **Action**: Crée une facture journalière pour chaque séjour en cours
- **Logs**: Enregistrés dans `logs/cron_hospitalization.log`

## Configuration Windows Task Scheduler

### Étape 1: Ouvrir le Planificateur de tâches
1. Appuyez sur `Win + R`
2. Tapez `taskschd.msc` et appuyez sur Entrée

### Étape 2: Créer une nouvelle tâche
1. Cliquez sur "Créer une tâche..." dans le panneau de droite
2. Onglet **Général**:
   - Nom: `Facturation Hospitalisation Quotidienne`
   - Description: `Génère les factures journalières pour les hospitalisations en cours`
   - Cochez "Exécuter même si l'utilisateur n'est pas connecté"
   - Cochez "Exécuter avec les autorisations maximales"

### Étape 3: Configurer le déclencheur
1. Onglet **Déclencheurs** → Nouveau
2. Commencer la tâche: `Selon une planification`
3. Paramètres:
   - Quotidien
   - Récurrence: tous les 1 jours
   - Heure: `00:01:00`
4. Cochez "Activé"
5. OK

### Étape 4: Configurer l'action
1. Onglet **Actions** → Nouveau
2. Action: `Démarrer un programme`
3. Programme/script: Chemin complet vers Python
   ```
   C:\Users\[VOTRE_USER]\Desktop\application_clinique\clinique_app\backend\venv\Scripts\python.exe
   ```
4. Ajouter des arguments:
   ```
   scripts/cron_hospitalization.py
   ```
5. Commencer dans:
   ```
   C:\Users\[VOTRE_USER]\Desktop\application_clinique\clinique_app\backend
   ```
6. OK

### Étape 5: Paramètres supplémentaires
1. Onglet **Conditions**:
   - Décochez "Démarrer la tâche uniquement si l'ordinateur est relié au secteur"
2. Onglet **Paramètres**:
   - Cochez "Autoriser l'exécution de la tâche à la demande"
   - Cochez "Exécuter la tâche dès que possible si un démarrage planifié est manqué"
3. OK

## Test Manuel

Pour tester le script manuellement avant de configurer le CRON:

```bash
cd clinique_app/backend
venv\Scripts\activate
python scripts/cron_hospitalization.py
```

Vérifiez ensuite le fichier `logs/cron_hospitalization.log` pour voir les résultats.

## Vérification des Logs

Les logs sont enregistrés dans `clinique_app/backend/logs/cron_hospitalization.log`

Exemple de sortie:
```
2026-04-06 00:01:00 - INFO - ================================================================================
2026-04-06 00:01:00 - INFO - DÉBUT DE LA FACTURATION JOURNALIÈRE DES HOSPITALISATIONS
2026-04-06 00:01:00 - INFO - Date: 2026-04-06 00:01:00
2026-04-06 00:01:00 - INFO - ================================================================================
2026-04-06 00:01:00 - INFO - Nombre de séjours en cours: 3
2026-04-06 00:01:01 - INFO - ✓ Facture créée: FACT-HOSPIT-2026-00001 - Patient: Dupont Jean - Chambre: 101 - Montant: 15000 FCFA - Jour: 5
2026-04-06 00:01:01 - WARNING - ⚠️ ALERTE - Patient: Martin Sophie (Chambre 205) - Acompte insuffisant: 50000 FCFA / Total accumulé: 75000 FCFA
2026-04-06 00:01:02 - INFO - ================================================================================
2026-04-06 00:01:02 - INFO - RÉSUMÉ DE LA FACTURATION
2026-04-06 00:01:02 - INFO - Factures créées: 3
2026-04-06 00:01:02 - INFO - Montant total facturé: 45000 FCFA
2026-04-06 00:01:02 - INFO - Alertes acompte insuffisant: 1
2026-04-06 00:01:02 - INFO - ================================================================================
2026-04-06 00:01:02 - INFO - FIN DE LA FACTURATION JOURNALIÈRE - SUCCÈS
```

## Alertes

Le script génère des alertes dans les cas suivants:
- **Acompte insuffisant**: Quand l'acompte versé est inférieur au total accumulé des nuitées

Ces alertes sont loguées avec le niveau WARNING et peuvent être utilisées pour envoyer des notifications aux responsables.

## Dépannage

### Le script ne s'exécute pas
1. Vérifiez que le chemin vers Python est correct
2. Vérifiez que l'environnement virtuel est activé
3. Vérifiez les permissions d'exécution

### Erreurs dans les logs
1. Vérifiez la connexion à la base de données
2. Vérifiez que les tables existent (migrations appliquées)
3. Vérifiez les permissions sur le dossier logs

### Tester l'exécution planifiée
1. Dans le Planificateur de tâches, clic droit sur la tâche
2. Sélectionnez "Exécuter"
3. Vérifiez les logs immédiatement après

## Notes Importantes

- Le script crée une facture par jour et par séjour
- Les factures sont en statut "en_attente" jusqu'à la sortie du patient
- À la sortie, toutes les factures quotidiennes sont consolidées dans la facture finale
- L'acompte est déduit du montant total à la sortie
