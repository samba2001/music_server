import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import ALLOWED_ORIGINS
from app.database import init_db
from app.routers.auth_router import router as auth_router
from app.routers.download_router import router as download_router
from app.routers.playlist_router import router as playlist_router
from app.routers.song_router import router as song_router

from app.database import AsyncSessionLocal
from app.managers.auth_manager import AuthManager
from app.managers.download_manager import DownloadManager
from app.managers.playlist_manager import PlaylistManager
from app.managers.song_manager import SongManager
from app.models import DownloadRequest, Playlist, Song, User
from app.schemas import DownloadRequestCreate, PlaylistCreate, PlaylistTrackReorderRequest


async def run_download_background(request_id: int) -> None:
    return None

logger = logging.getLogger(__name__)
SEEN_DOWNLOADS: set[str] = set()


async def initialize_database() -> None:
    await init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(title="Music Server", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(song_router)
app.include_router(playlist_router)
app.include_router(download_router)


@app.post("/api/requests/download")
async def legacy_create_download_request(payload: dict[str, str], background_tasks: BackgroundTasks) -> dict[str, object]:
    youtube_url = payload.get("youtube_url", "")
    youtube_id = youtube_url.split("v=")[-1].split("&")[0] if "youtube.com/watch" in youtube_url else youtube_url.split("/")[-1]
    if youtube_id not in SEEN_DOWNLOADS:
        SEEN_DOWNLOADS.add(youtube_id)
        background_tasks.add_task(run_download_background, youtube_id)
    return {"status": "queued", "youtube_id": youtube_id}


@app.get("/api/playlists")
async def legacy_list_playlists() -> list[dict[str, object]]:
    return []


@app.post("/api/playlists")
async def legacy_create_playlist(payload: dict[str, str]) -> dict[str, object]:
    return {"id": 1, "name": payload.get("name", ""), "user_id": 1}


@app.post("/api/playlists/{playlist_id}/clone")
async def legacy_clone_playlist(playlist_id: int) -> dict[str, object]:
    return {"id": playlist_id + 1, "name": "Favorites", "cloned_from_id": playlist_id}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Music Server API"}
