"""
CrisisLens - Trust-Aware Emergency Intelligence System
Member 2: Backend, Database & Integration Lead
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import (
    CrisisLensException,
    crisislens_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from app.routers import (
    reports,
    verification,
    priority,
    evidence,
    incidents,
    analysis,
    simulations,
)

app = FastAPI(
    title="CrisisLens API",
    description="Trust-Aware Emergency Intelligence System API - Contract v1.0",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration strictly matching API Contract v1.0
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Exception Handlers enforcing standard API Contract error shape
app.add_exception_handler(CrisisLensException, crisislens_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API Routers in exact precedence order
app.include_router(verification.router)    # PATCH /reports/{id}/verify
app.include_router(reports.router)         # POST /reports, GET /reports, GET /reports/{id}
app.include_router(priority.router)        # GET /incidents/priority
app.include_router(evidence.router)        # GET /incidents/{id}/evidence-graph
app.include_router(incidents.router)       # GET /incidents, GET /incidents/{id}
app.include_router(analysis.router)        # POST /analyze/{report_id}
app.include_router(simulations.router)     # POST /simulate


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "crisislens-backend",
        "version": "1.0.0",
    }
