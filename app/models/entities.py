from datetime import datetime, timezone
from enum import Enum
import uuid
from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Column, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlaylistType(str, Enum):
    DEFAULT = "default"
    USER = "user"


class ActionType(str, Enum):
    SONG_PLAYED = "SONG_PLAYED"
    PLAYLIST_CLONED = "PLAYLIST_CLONED"
    ADD_SONG = "ADD_SONG"
    REMOVE_SONG = "REMOVE_SONG"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    playlists: Mapped[list["Playlist"]] = relationship(back_populates="user")
    history: Mapped[list["History"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
    back_populates="user", cascade="all, delete-orphan"
)

class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    languages: Mapped[str] = mapped_column(Text, default="")
    profile_pic: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    songs: Mapped[list["Song"]] = relationship(back_populates="author")


class Song(Base):
    __tablename__ = "songs"
    __table_args__ = (Index("ix_songs_search_params", "search_params"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(512), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("authors.id", ondelete="SET NULL"), nullable=True)
    mp3_path: Mapped[str] = mapped_column(String(1024))
    search_params: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    author: Mapped[Author | None] = relationship(back_populates="songs")
    song_metadata: Mapped["SongMetaData | None"] = relationship(back_populates="song", cascade="all, delete-orphan", uselist=False)
    playlist_links: Mapped[list["PlaylistSong"]] = relationship(back_populates="song")


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    playlist_type: Mapped[PlaylistType] = mapped_column(SqlEnum(PlaylistType), default=PlaylistType.USER)
    is_clone: Mapped[bool] = mapped_column(Boolean, default=False)
    clone_id: Mapped[int | None] = mapped_column(ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    user: Mapped[User | None] = relationship(back_populates="playlists")
    songs: Mapped[list["PlaylistSong"]] = relationship(back_populates="playlist", cascade="all, delete-orphan")
    clone_of: Mapped["Playlist | None"] = relationship(remote_side=[id], back_populates="clones")
    clones: Mapped[list["Playlist"]] = relationship(back_populates="clone_of")


class PlaylistSong(Base):
    __tablename__ = "playlist_song_mapping"
    __table_args__ = (UniqueConstraint("playlist_id", "song_id", name="uq_playlist_song"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id", ondelete="CASCADE"), index=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    playlist: Mapped[Playlist] = relationship(back_populates="songs")
    song: Mapped[Song] = relationship(back_populates="playlist_links")


class SongMetaData(Base):
    __tablename__ = "song_meta_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), unique=True)
    song_lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    song: Mapped[Song] = relationship(back_populates="song_metadata")


class History(Base):
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id", ondelete="SET NULL"), nullable=True)
    playlist_id: Mapped[int | None] = mapped_column(ForeignKey("playlists.id", ondelete="SET NULL"), nullable=True)
    action_type: Mapped[ActionType] = mapped_column(SqlEnum(ActionType))
    played_till: Mapped[int] = mapped_column(Integer, default=0)
    passed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    user: Mapped[User] = relationship(back_populates="history")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Changed from UUID to Integer to match User.id
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")