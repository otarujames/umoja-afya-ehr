from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import PROJECT_ROOT, get_settings
from .database import Base, SessionLocal, engine
from . import enterprise_models  # noqa: F401 - registers enterprise tables
from . import operational_models  # noqa: F401 - registers operational tables
from . import enhancement_models  # noqa: F401 - registers enhancement tables
from . import collaboration_models  # noqa: F401 - registers collaboration tables
from .routers import audit, auth, collaboration, enterprise, enhancements, facilities, fhir, flowsheets, health, modules, operations, orders, patients, registration, tracker
from .seed import seed_database
from .security import optional_user
from .rbac import RoleGateMiddleware
from .middleware import BodySizeLimitMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from .version import __version__

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_runtime()
    if settings.schema_auto_create:
        Base.metadata.create_all(bind=engine)
    if settings.seed_demo_data and settings.environment.lower() in {"development", "test"}:
        with SessionLocal() as db:
            seed_database(db)
    yield


docs_enabled = settings.api_docs_enabled
app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Umoja Afya Tanzania enterprise electronic health record. "
        "Includes national MPI and patient registration, scheduling/referrals, ADT and unit management, longitudinal documentation, orders/results, flowsheets/eMAR, pharmacy, revenue cycle, supply chain, quality, public health, remote care, FHIR and audit. Patient-facing portal delivery is intentionally deferred from this release."
    ),
    openapi_url=f"{settings.api_prefix}/openapi.json" if docs_enabled else None,
    docs_url=f"{settings.api_prefix}/docs" if docs_enabled else None,
    redoc_url=f"{settings.api_prefix}/redoc" if docs_enabled else None,
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Break-Glass-Reason"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RoleGateMiddleware)

for public_router in [health.router, auth.router, facilities.router, modules.router]:
    app.include_router(public_router, prefix=settings.api_prefix)

for protected_router in [
    patients.router,
    registration.router,
    tracker.router,
    flowsheets.router,
    orders.router,
    audit.router,
    enterprise.router,
    fhir.router,
    operations.router,
    enhancements.router,
    collaboration.router,
]:
    app.include_router(protected_router, prefix=settings.api_prefix, dependencies=[Depends(optional_user)])


frontend_dir = PROJECT_ROOT / "frontend"
app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="assets")


@app.get("/manifest.json", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(frontend_dir / "manifest.json")


@app.get("/service-worker.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(frontend_dir / "service-worker.js", media_type="application/javascript")


@app.get("/styles.css", include_in_schema=False)
def styles() -> FileResponse:
    return FileResponse(frontend_dir / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def javascript() -> FileResponse:
    return FileResponse(frontend_dir / "app.js", media_type="application/javascript")


@app.get("/{full_path:path}", include_in_schema=False)
def frontend(full_path: str) -> FileResponse:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    requested = frontend_dir / full_path
    if full_path and requested.is_file() and requested.resolve().is_relative_to(frontend_dir.resolve()):
        return FileResponse(requested)
    return FileResponse(frontend_dir / "index.html")
