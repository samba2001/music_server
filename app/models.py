from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    youtube_id = Column(String(64), unique=True, nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    language = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    artists = relationship("SongArtist", back_populates="song", cascade="all, delete-orphan")
    lyrics = relationship("Lyrics", back_populates="song", uselist=False, cascade="all, delete-orphan")


class SongArtist(Base):
    __tablename__ = "song_artists"

    song_id = Column(Integer, ForeignKey("songs.id"), primary_key=True)
    artist_id = Column(Integer, ForeignKey("artists.id"), primary_key=True)

    song = relationship("Song", back_populates="artists")
    artist = relationship("Artist")


class Lyrics(Base):
    __tablename__ = "lyrics"

    id = Column(Integer, primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"), unique=True, nullable=False)
    source = Column(String(64), nullable=False, default="LRCLIB")
    synced_lyrics = Column(JSON, nullable=True)
    plain_text = Column(Text, nullable=True)

    song = relationship("Song", back_populates="lyrics")


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    is_template = Column(Boolean, nullable=False, default=False)
    cloned_from_id = Column(Integer, ForeignKey("playlists.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan")


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    playlist_id = Column(Integer, ForeignKey("playlists.id"), primary_key=True)
    song_id = Column(Integer, ForeignKey("songs.id"), primary_key=True)
    position = Column(Integer, nullable=False, default=0)

    playlist = relationship("Playlist", back_populates="tracks")
    song = relationship("Song")


class DownloadRequest(Base):
    __tablename__ = "download_requests"

    id = Column(Integer, primary_key=True)
    youtube_url = Column(String(2048), nullable=False)
    youtube_id = Column(String(64), nullable=False, index=True)
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(32), nullable=False, default="queued")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
