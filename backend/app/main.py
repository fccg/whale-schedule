import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.database import close_db, get_db
from app.providers.base import ProviderError
from app.routers import auth, gpus, instances, agent, budget, tests

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    degraded_task = asyncio.create_task(_degraded_check_loop())
    yield
    degraded_task.cancel()
    await close_db()


async def _degraded_check_loop():
    await asyncio.sleep(5)
    while True:
        try:
            from app.services.instance_service import check_degraded_instances
            await check_degraded_instances()
        except Exception:
            logger.warning("degraded check loop error", exc_info=True)
        await asyncio.sleep(15)


app = FastAPI(title="GPU Scheduling Platform", lifespan=lifespan)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGIN", "http://localhost:3000,http://115.191.43.252:18761").split(",")
    if origin.strip()
]


@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    logger.warning("Provider error: %s — %s", exc.provider, exc.detail)
    return JSONResponse(
        status_code=502,
        content={"error": "PROVIDER_ERROR", "message": f"{exc.provider}: {exc.detail}"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(gpus.router)
app.include_router(instances.router)
app.include_router(agent.router)
app.include_router(budget.router)
app.include_router(tests.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    try:
        db = await get_db()
        await db.execute("SELECT 1")
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        logger.warning("Readiness check failed", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "error"},
        )


@app.get("/")
async def root():
    return {"service": "GPU Scheduling Platform", "status": "running"}
