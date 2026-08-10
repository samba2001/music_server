# music_server

A production-style FastAPI backend for a self-hosted music server built with Python 3.11+, SQLite, SQLAlchemy 2.0, and async support via aiosqlite.

## Features

- FastAPI application with CORS support for local frontend development
- Async SQLite database with SQLAlchemy 2.0 models
- Manager / repository / router architecture for clean separation of concerns
- Authentication bypass layer for local/dev use via BYPASS_AUTH
- Download request handling and playlist/song endpoints
- Media storage under storage/media

## Project structure

- app/main.py - FastAPI app entrypoint and compatibility routes
- app/config.py - configuration and logging
- app/database.py - async database session setup
- app/models.py - SQLAlchemy ORM models
- app/schemas.py - Pydantic request/response schemas
- app/managers/ - business logic managers
- app/repositories/ - database access layer
- app/routers/ - API route handlers

## Requirements

- Python 3.11+
- SQLite
- FastAPI
- SQLAlchemy 2.0
- aiosqlite
- google-auth
- yt-dlp
- httpx

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

4. Health check:
   ```bash
   curl http://127.0.0.1:8000/health
   ```

## Configuration

Environment variables:

- DATABASE_URL - SQLite connection string (defaults to sqlite+aiosqlite:///./music_server.db)
- BYPASS_AUTH - Set to True for local/dev auth bypass (default: True)
- GOOGLE_CLIENT_ID - Google OAuth client ID when BYPASS_AUTH is False

## API overview

### Auth
- POST /api/v1/auth/google
- GET /api/v1/users/me

### Downloads
- POST /api/v1/requests/download
- GET /api/v1/requests
- GET /api/v1/requests/{id}

### Songs
- GET /api/v1/songs
- GET /api/v1/songs/{id}
- GET /api/v1/songs/{id}/stream
- GET /api/v1/songs/{id}/lyrics
- DELETE /api/v1/songs/{id}

### Playlists
- GET /api/v1/playlists
- POST /api/v1/playlists
- POST /api/v1/playlists/{id}/clone
- PUT /api/v1/playlists/{id}/tracks
- DELETE /api/v1/playlists/{id}

### Compatibility routes
- GET /health
- POST /api/requests/download
- GET /api/playlists
- POST /api/playlists
- POST /api/playlists/{id}/clone

## Testing

Run the regression tests:

```bash
pytest -q
```
