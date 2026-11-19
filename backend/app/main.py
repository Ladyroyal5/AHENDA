
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.api.patients import router as patients_router
from app.api.auth import router as auth_router
from app.api.screening_results import router as screening_results_router
from app.api.care_cases import router as care_cases_router
from app.api import escalations
from app.api import dashboard
from app.api import referrals
from app.api import clinical_outcomes
from app.api import risk_assessments
from app.api import interventions
from app.api import communication

# 1. Create the FastAPI application FIRST
app = FastAPI(
    title="AHENDA Health API",
    description="Intelligent Healthcare Continuity Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Register the patient routes AFTER creating app
# 2. Register API routes
app.include_router(patients_router)
app.include_router(auth_router)
app.include_router(screening_results_router)
app.include_router(care_cases_router)
app.include_router(escalations.router)
app.include_router(dashboard.router)
from app.api import tasks
app.include_router(tasks.router)
app.include_router(referrals.router)
app.include_router(clinical_outcomes.router)
app.include_router(risk_assessments.router)
app.include_router(interventions.router)
app.include_router(communication.router)


# 3. Homepage
@app.get("/")
def home():
    return {
        "application": "AHENDA Health",
        "message": "No Result Left Behind. "
                   "No Patient Lost in Transition.",
        "status": "operational"
    }


# 4. Application health check
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": "AHENDA"
    }


# 5. Database health check
@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT DATABASE()"))

    return {
        "database": result.scalar(),
        "connection": "successful"
    }
