# Music Server API

Async FastAPI backend for local music streaming, YouTube audio ingestion, playlists, and playback history.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
uv run music-server
```

The default database is SQLite. Set `DATABASE_URL` to an async PostgreSQL URL such as `postgresql+asyncpg://user:password@host/database` for PostgreSQL.

Audio is stored in `media/songs/`. YouTube downloads require `ffmpeg` on the system PATH.

Make a user admin:

1. Edit `scripts/make_user_admin.py` and set `DEFAULT_EMAIL` to the email you want to promote.
2. Run the script (no flags required):

```bash
source .venv/bin/activate
python -m scripts.make_user_admin
```

## Playlist creation and song management API

Authenticated users, including admins, can create and edit their own user playlists.
Only admins can create or modify default playlists. A playlist song can be added using
either an existing `song_id` or a YouTube URL; when given a URL, the server downloads
the audio, creates the library song if needed, and maps it to the playlist.

Create a user playlist:

```bash
curl --request POST 'http://127.0.0.1:8000/api/v1/playlists/' \
  --header 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{"name":"My playlist"}'
```

Add an existing song by ID:

```bash
curl --request POST 'http://127.0.0.1:8000/api/v1/playlists/PLAYLIST_ID/songs' \
  --header 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{"song_id":42}'
```

Or import a YouTube song and add it in the same request:

```bash
curl --request POST 'http://127.0.0.1:8000/api/v1/playlists/PLAYLIST_ID/songs' \
  --header 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  --header 'Content-Type: application/json' \
  --data '{"youtube_url":"https://www.youtube.com/watch?v=VIDEO_ID"}'
```

Use `GET /api/v1/playlists/` to list the authenticated user's playlists,
`GET /api/v1/playlists/default` to list default playlists, and
`GET /api/v1/songs/search?q=QUERY` to find existing songs. Provide exactly one of
`song_id` or `youtube_url`. An already-mapped song returns `409 Conflict`; missing
songs return `404`; non-admin attempts to modify default playlists return `403`.

Alembic migrations
------------------

This project includes a minimal Alembic scaffold in `alembic/`. To apply the `is_admin` migration (adds the `is_admin` column to `users`):

1. Install Alembic: `pip install alembic`
2. Initialize (not needed here — scaffold already present) then run:

```bash
alembic upgrade head
```

Notes:
- The `alembic/env.py` reads the database URL from `app.core.config.settings.database_url`.
- For production workflow, prefer creating and tracking migrations with `alembic revision --autogenerate -m "msg"` rather than editing files by hand.
