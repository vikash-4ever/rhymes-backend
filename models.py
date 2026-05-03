from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid


# Association Table
song_artists = Table(
    "song_artists",
    Base.metadata,
    Column("song_id", String, ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True),
    Column("artist_id", String, ForeignKey("artists.id", ondelete="CASCADE"), primary_key=True),
)


class Song(Base):
    __tablename__ = "songs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    album = Column(String)
    genre = Column(String)
    duration_seconds = Column(Integer)

    audio_url = Column(String)
    thumbnail_url = Column(String)
    lyrics_url = Column(String)

    play_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    artists = relationship("Artist", secondary=song_artists, back_populates="songs")


class Artist(Base):
    __tablename__ = "artists"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)

    songs = relationship("Song", secondary=song_artists, back_populates="artists")