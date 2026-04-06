"""Erreurs SQLAlchemy → HTTP : messages exploitables côté client (login, accueil, etc.)."""

from fastapi import HTTPException, status


def http_exception_from_db_error(exc: Exception) -> HTTPException:
    msg = str(exc).lower()
    orig = getattr(exc, "orig", exc)
    orig_s = str(orig).lower() if orig is not None else ""
    combined = f"{msg} {orig_s}"
    if (
        "doesn't exist" in combined
        or "1146" in combined
        or "no such table" in combined
    ):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Table SQL manquante. Dans le dossier backend, exécutez : "
                "alembic upgrade head"
            ),
        )
    if any(
        x in combined
        for x in (
            "can't connect",
            "2003",
            "refused",
            "actively refused",
            "unknown mysql server host",
            "timed out",
            "1045",
            "access denied",
            "lost connection",
        )
    ):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Impossible de joindre MySQL ou accès refusé. Vérifiez que WAMP / MariaDB "
                "est démarré, que la base clinique_db existe, et DATABASE_URL dans .env "
                "(utilisateur, mot de passe, port 3306)."
            ),
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Erreur base de données. Vérifiez MySQL et le fichier .env — détail dans le "
            "terminal Uvicorn."
        ),
    )
