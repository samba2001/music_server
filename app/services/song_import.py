import logging
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Author, Song, SongMetaData
from app.services.downloader import DownloadError, download_audio, probe_audio_info

logger = logging.getLogger(__name__)


def clean_youtube_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "v" in query:
        parsed = parsed._replace(query=urlencode({"v": query["v"][0]}))
    return urlunparse(parsed)


async def get_or_create_youtube_song(
    db: AsyncSession,
    youtube_url: str,
) -> tuple[Song, bool]:
    """Resolve a YouTube URL to a library song, downloading and creating it if needed."""
    cleaned_url = clean_youtube_url(youtube_url)
    try:
        probed_info = await probe_audio_info(cleaned_url)
    except DownloadError:
        logger.exception("Unable to inspect YouTube URL")
        raise

    video_mp3 = f"{probed_info['id']}.mp3"
    existing = await db.scalar(
        select(Song).where(
            (Song.mp3_path == video_mp3)
            | Song.search_params.ilike(f"%{probed_info['id']}%")
            | Song.search_params.ilike(f"%{probed_info['webpage_url']}%")
        )
    )
    if existing is not None:
        return existing, False

    try:
        info: dict[str, Any] = await download_audio(cleaned_url)
    except DownloadError:
        logger.exception("Unable to download YouTube audio")
        raise

    author = await db.scalar(select(Author).where(Author.name == info["uploader"]))
    if author is None:
        author = Author(name=info["uploader"])
        db.add(author)
        await db.flush()

    song = Song(
        name=info["title"],
        author=author,
        mp3_path=f"{info['id']}.mp3",
        search_params=f"{info['title']} {info['uploader']} {info['webpage_url']}",
    )
    db.add(song)
    await db.flush()
    db.add(SongMetaData(song_id=song.id))
    await db.flush()
    return song, True
