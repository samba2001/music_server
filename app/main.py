import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1 import auth, history, playlists, songs, users
from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("music_server")

# Explicit origins are required when allow_credentials=True
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "https://music.kuluru.in",
    "https://my-music-app-ui.reddy200101.workers.dev",
]
@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting application startup")
    await init_db()
    logger.info("Database initialization complete")
    yield
    logger.info("Application shutdown complete")


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

# Pass the explicit origins list instead of ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(playlists.router, prefix="/api/v1")
app.include_router(songs.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    logger.info("Health check requested")
    return {"status": "ok"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    
    for path, path_obj in openapi_schema.get("paths", {}).items():
        for operation in path_obj.values():
            if path == "/api/v1/auth/google":
                continue
            operation.setdefault("security", []).append({"bearerAuth": []})
            
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi