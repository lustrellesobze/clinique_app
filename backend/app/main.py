from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import engine
from app.routers import (
    accueil,
    audit,
    auth,
    consultations,
    doctor,
    dashboard,
    hospitalization,
    imaging,
    insurance,
    invoices,
    laboratory,
    notifications,
    patients,
    payments,
    pharmacy,
    prescriptions,
    users,
    webhooks,
)

app = FastAPI(
    title="Clinique — Facturation",
    description="API FastAPI — logiciel de facturation clinique",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    # Autres ports / hôtes locaux (ex. ng serve sur un port différent)
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(accueil.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(consultations.router, prefix="/api")
app.include_router(doctor.router, prefix="/api")
app.include_router(prescriptions.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(pharmacy.router, prefix="/api")
app.include_router(laboratory.router, prefix="/api")
app.include_router(imaging.router, prefix="/api")
app.include_router(hospitalization.router, prefix="/api")
app.include_router(insurance.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(webhooks.ws_router, prefix="/api")


@app.get("/")
def root():
    """Point d’entrée : la racine n’est pas une route métier (tout est sous /api)."""
    return {
        "service": "Clinique — Facturation API",
        "version": app.version,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
        "api": "/api",
    }


@app.get("/health")
def health():
    """Vérifie aussi MySQL : la racine `/` ne touche pas à la base."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "unreachable",
                "hint": (
                    "Démarrez WAMP / MariaDB, créez la base clinique_db si besoin, "
                    "puis vérifiez DATABASE_URL dans backend/.env"
                ),
            },
        )
    return {"status": "ok", "database": "connected"}
