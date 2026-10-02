from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm.exc import StaleDataError

from .adapters import fetch_sentinel
from .api import router
from .health_api import router as health_router
from .config import Settings
from .db import make_engine, make_sessions


def create_app(settings: Settings | None = None, *, engine=None, catalogue_fetcher=fetch_sentinel):
    settings = settings or Settings.from_env()
    engine = engine or make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        # Schema changes are explicit migrations, never incidental API startup side effects.
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM registry_alembic_version")).scalar()
            if revision != "0007_dashboard_rbac":
                raise RuntimeError("Run the registry database migrations before starting the API")
        yield
        engine.dispose()

    app = FastAPI(title="Synetra CCTV Registry", version="1.0.0", lifespan=lifespan,
                  description="Vendor-neutral camera metadata and GIS API. Real catalogues only; media/analytics run separately.")
    app.state.settings = settings
    app.state.sessions = make_sessions(engine)
    app.state.catalogue_fetcher = catalogue_fetcher
    app.include_router(router)
    app.include_router(health_router)
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                           allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                           allow_headers=["Authorization", "Content-Type", "If-Match"],
                           expose_headers=["ETag", "X-Request-ID"], allow_credentials=True)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(uuid4())
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, error):
        return JSONResponse(status_code=409, content={"detail": "duplicate_or_invalid_reference"})

    @app.exception_handler(StaleDataError)
    async def revision_error(request, error):
        return JSONResponse(status_code=409, content={"detail": "concurrent_update_retry_with_current_revision"})

    @app.exception_handler(OperationalError)
    async def database_error(request, error):
        return JSONResponse(status_code=503, content={"detail": "registry_database_unavailable"})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Do not echo unrecognized credential fields or raw input into errors.
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(e["loc"]), "type": e["type"], "msg": e["msg"]} for e in error.errors()]})

    @app.get("/health", tags=["operations"])
    def health():
        with engine.connect() as connection:
            connection.execute(text("SELECT id FROM registry_vendors LIMIT 1"))
        return {"status": "ok", "service": "synetra-registry"}

    return app
