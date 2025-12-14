from dotenv import load_dotenv
load_dotenv()

import os
import time
import uuid
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_conn
from app.routers import (
    metadata,
    map as map_router,
    timeline,
    events,
    articles,
    country_summary,
    country,
)

app = FastAPI(title="WhoGoverns API", version="1.0.0")

# -----------------------------
# Logging (observability)
# -----------------------------
logger = logging.getLogger("whogoverns")
logging.basicConfig(level=logging.INFO)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.time()

    response = await call_next(request)

    duration_ms = int((time.time() - start) * 1000)
    response.headers["x-request-id"] = request_id

    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# -----------------------------
# Cache headers (controlled caching)
# -----------------------------
@app.middleware("http")
async def cache_headers(request: Request, call_next):
    response = await call_next(request)

    path = request.url.path
    cache = "no-store"

    if path.startswith("/v1/metadata"):
        cache = "public, max-age=86400"  # 24h
    elif path.startswith("/v1/map") or path.startswith("/v1/timeline"):
        cache = "public, max-age=3600"   # 1h
    elif path.startswith("/v1/events") or path.startswith("/v1/articles"):
        cache = "public, max-age=600"    # 10 min

    response.headers["Cache-Control"] = cache
    return response


# -----------------------------
# CORS (prod vs dev)
# -----------------------------
env = os.getenv("ENV", "dev")

if env == "prod":
    allowed_origins = [
        "https://whogoverns.org",
        "https://www.whogoverns.org",
    ]
else:
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# -----------------------------
# Core endpoints
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    try:
        with get_conn() as conn:
            conn.execute("select 1").fetchone()
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "db": "error", "error": str(e)[:200]}


@app.get("/version")
def version():
    return {
        "service": "whogoverns-api",
        "git_sha": os.getenv("GIT_SHA"),
        "render_service_id": os.getenv("RENDER_SERVICE_ID"),
        "env": env,
    }


# -----------------------------
# API routers
# -----------------------------
app.include_router(metadata.router, prefix="/v1", tags=["metadata"])
app.include_router(map_router.router, prefix="/v1", tags=["map"])
app.include_router(timeline.router, prefix="/v1", tags=["timeline"])
app.include_router(events.router, prefix="/v1", tags=["events"])
app.include_router(articles.router, prefix="/v1", tags=["articles"])
app.include_router(country.router, prefix="/v1", tags=["country"])
app.include_router(country_summary.router, prefix="/v1", tags=["country"])
