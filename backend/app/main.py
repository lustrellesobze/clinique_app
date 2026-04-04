from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    audit,
    auth,
    consultations,
    dashboard,
    hospitalization,
    imaging,
    insurance,
    invoices,
    laboratory,
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(consultations.router, prefix="/api")
app.include_router(prescriptions.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(pharmacy.router, prefix="/api")
app.include_router(laboratory.router, prefix="/api")
app.include_router(imaging.router, prefix="/api")
app.include_router(hospitalization.router, prefix="/api")
app.include_router(insurance.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
