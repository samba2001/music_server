import logging
import shutil
import yt_dlp
import httpx
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import STORAGE_DIR
from app.models import DownloadRequest
from app.repositories.download_repository import DownloadRepository
from app.managers.song_manager import SongManager

logger = logging.getLogger(__name__)


class DownloadManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.download_repo = DownloadRepository(session)
        self.song_manager = SongManager(session)

    async def create_download_request(self, *, youtube_url: str, user_id: int | None) -> DownloadRequest:
        youtube_id = self._extract_youtube_id(youtube_url)
        existing = await self.download_repo.get_by_youtube_id(youtube_id)
        if existing is not None:
            return existing
        return await self.download_repo.create(youtube_url=youtube_url, youtube_id=youtube_id, requested_by_user_id=user_id)

    async def get_request(self, request_id: int) -> DownloadRequest:
        request = await self.download_repo.get_by_id(request_id)
        if request is None:
            raise HTTPException(status_code=404, detail="Download request not found")
        return request

    async def list_requests(self) -> list[DownloadRequest]:
        return await self.download_repo.list()

    async def process_download(self, request_id: int) -> None:
        request = await self.get_request(request_id)
        try:
            logger.info("Starting download for %s", request.youtube_id)
            STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            output_path = STORAGE_DIR / f"{request.youtube_id}.opus"
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": str(output_path),
                "quiet": True,
                "noplaylist": True,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "opus", "preferredquality": "0"}],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(request.youtube_url, download=True)
            title = (info or {}).get("title") or request.youtube_id
            artist_name = (info or {}).get("artist") or (info or {}).get("uploader") or "Unknown Artist"
            duration = int((info or {}).get("duration") or 0)
            lyrics_payload = await self._fetch_lyrics(title=title, artist_name=artist_name)
            song = await self.song_manager.save_downloaded_song(
                title=title,
                duration_seconds=duration,
                youtube_id=request.youtube_id,
                file_path=str(output_path),
                artist_name=artist_name,
                lyrics_payload=lyrics_payload,
                language="en",
            )
            request.status = "completed"
            request.error_message = None
            await self.session.commit()
            logger.info("Completed download for %s", request.youtube_id)
        except Exception as exc:
            request.status = "failed"
            request.error_message = str(exc)
            await self.session.commit()
            logger.exception("Download failed for %s", request.youtube_id)

    async def _fetch_lyrics(self, *, title: str, artist_name: str) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://lrclib.net/api/get", params={"track_name": title, "artist_name": artist_name})
                if response.status_code == 200:
                    payload = response.json()
                    if isinstance(payload, dict):
                        raw = payload.get("syncedLyrics") or payload.get("lyrics") or ""
                        if isinstance(raw, str):
                            return self._parse_lrc(raw)
                        return payload.get("syncedLyrics") or []
                    if isinstance(payload, list):
                        return payload
        except Exception as exc:
            logger.warning("Lyrics fetch failed: %s", exc)
        return []

    def _parse_lrc(self, value: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for line in value.splitlines():
            if not line.startswith("[") or "]" not in line:
                continue
            stamp, lyric = line.split("]", 1)
            stamp = stamp[1:]
            if ":" not in stamp:
                continue
            minutes, seconds = stamp.split(":", 1)
            try:
                time_value = (float(minutes) * 60) + float(seconds)
            except ValueError:
                continue
            text_value = lyric.strip()
            if text_value:
                entries.append({"time": round(time_value, 3), "text": text_value})
        return entries

    def _extract_youtube_id(self, url: str) -> str:
        if "youtube.com/watch" in url:
            return url.split("v=")[-1].split("&")[0]
        if "youtu.be/" in url:
            return url.split("youtu.be/")[-1].split("?")[0]
        return url.split("/")[-1]
