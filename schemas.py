from pydantic import BaseModel
from typing import List
from datetime import datetime


class ArtistResponse(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class SongResponse(BaseModel):
    id: str
    title: str
    album: str | None
    genre: str | None
    duration_seconds: int
    audio_url: str | None
    thumbnail_url: str | None
    lyrics_url: str | None
    play_count: int
    created_at: datetime
    artists: List[ArtistResponse]

    class Config:
        from_attributes = True