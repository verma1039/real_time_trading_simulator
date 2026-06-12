from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import add_request_logging, setup_logging
from app.core.rate_limit import setup_rate_limiting
from app.db import engine
from app.routes import api_v1

settings = get_settings()

# Initialise structured logging before anything else
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
add_request_logging(app)

# ── Error handlers ───────────────────────────────────────────────
register_error_handlers(app)
setup_rate_limiting(app)

# ── Routers ──────────────────────────────────────────────────────
app.include_router(api_v1, prefix=settings.api_v1_prefix)


# ── System endpoints (outside /api/v1) ───────────────────────────
@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}

# touch
