# Tests backend (pytest)

## En CI (GitHub Actions)

Le workflow `.github/workflows/ci.yml` :

1. Démarre MySQL 8
2. Applique `alembic upgrade head`
3. Lance `pytest`

Aucune configuration locale requise sur le runner.

## En local (comme le pipeline)

Prérequis : MySQL/MariaDB accessible (WAMP ou Docker).

```powershell
cd backend
$env:DATABASE_URL = "mysql+pymysql://root@127.0.0.1:3306/clinique_db?charset=utf8mb4"
$env:SECRET_KEY = "ci-test-secret-key-at-least-32-characters-long!!"
alembic upgrade head
pytest -v
```

Ou avec la base de test dédiée :

```powershell
$env:DATABASE_URL = "mysql+pymysql://root@127.0.0.1:3306/clinique_test?charset=utf8mb4"
```

Créez la base `clinique_test` dans phpMyAdmin si nécessaire.
