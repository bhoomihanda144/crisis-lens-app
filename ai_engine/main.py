"""CrisisLens AI Engine Microservice Entrypoint.

Runs on port 8001.
Member 3 – AI/ML Developer component.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_engine import __version__
from ai_engine.api.routes import router

app = FastAPI(
    title="CrisisLens AI Engine",
    description="Trust-Aware Emergency Intelligence AI Engine Microservice",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration allowing frontend and backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router)


def start() -> None:
    """Entry point to launch the microservice via Uvicorn on port 8001."""
    import uvicorn
    uvicorn.run("ai_engine.main:app", host="127.0.0.1", port=8001, reload=True)


if __name__ == "__main__":
    start()
