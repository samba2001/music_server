import asyncio
import logging
import re
from pathlib import Path
from typing import Any

import yt_dlp

from app.core.config import settings

logger = logging.getLogger(__name__)


class DownloadError(RuntimeError):
    pass


def _safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._")[:180] or "track"


def _download(url: str, output_dir: Path) -> dict[str, Any]:
    logger.info("Starting YouTube download for URL: %s", url)
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": True,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
      "postprocessors": [{
          "key": "FFmpegExtractAudio",
          "preferredcodec": "mp3",
          "preferredquality": "192",
      }],
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            logger.info("Extracting YouTube metadata and downloading audio")
            info = downloader.extract_info(url, download=True)
            if info is None:
                logger.warning("yt-dlp returned no info for URL: %s", url)
                raise DownloadError("yt-dlp returned no media information")
            video_id = _safe_filename(str(info.get("id", "track")))
            result = {
                "id": video_id,
                "title": info.get("title") or "Untitled",
                "uploader": info.get("uploader") or "Unknown artist",
                "webpage_url": info.get("webpage_url", url),
            }
            logger.info("YouTube download completed for video_id=%s title=%s", result["id"], result["title"])
            return result
    except Exception as exc:
        logger.exception("YouTube download failed for URL: %s", url)
        raise DownloadError("Unable to download audio from YouTube") from exc


async def download_audio(url: str) -> dict[str, Any]:
    settings.media_root.mkdir(parents=True, exist_ok=True)
    try:
        return await asyncio.wait_for(asyncio.to_thread(_download, url, settings.media_root), settings.download_timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise DownloadError("Audio download timed out") from exc


def _get_info_no_download(url: str) -> dict[str, Any]:
    logger.info("Probing YouTube metadata for URL: %s", url)
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=False)
            if info is None:
                logger.warning("No YouTube metadata returned for URL: %s", url)
                raise DownloadError("yt-dlp returned no media information")
            video_id = _safe_filename(str(info.get("id", "track")))
            result = {
                "id": video_id,
                "title": info.get("title") or "Untitled",
                "uploader": info.get("uploader") or "Unknown artist",
                "webpage_url": info.get("webpage_url", url),
            }
            logger.info("YouTube metadata resolved for video_id=%s title=%s", result["id"], result["title"])
            return result
    except Exception as exc:
        logger.exception("YouTube metadata probe failed for URL: %s", url)
        raise DownloadError("Unable to fetch media info from YouTube") from exc


async def probe_audio_info(url: str) -> dict[str, Any]:
    """Fetches metadata for a YouTube URL without downloading the media.

    Returns the same info dict as `download_audio` but does not download the file.
    """
    try:
        return await asyncio.to_thread(_get_info_no_download, url)
    except Exception as exc:
        raise DownloadError(str(exc)) from exc
