from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from database import SessionLocal, engine
from models import Base, Song, Artist
from schemas import SongResponse
from typing import List
import requests

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"message": "Rhymes API Running 🎵"}

@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}

@app.get("/songs", response_model=list[SongResponse])
def get_songs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Song).offset(skip).limit(limit).all()

@app.get("/songs/{song_id}", response_model=SongResponse)
def get_song(song_id: str, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    return song

@app.post("/songs/by-ids", response_model=List[SongResponse])
def get_songs_by_ids(
    ids: List[str] = Body(...),
    db: Session = Depends(get_db)
):
    songs = db.query(Song).filter(Song.id.in_(ids)).all()
    return songs

@app.get("/search", response_model=list[SongResponse])
def search_songs(q: str, db: Session = Depends(get_db)):

    normalized_query = q.replace("-", " ").strip().lower()

    return (
        db.query(Song)
        .join(Song.artists)
        .filter(
            or_(
                func.lower(Song.title).ilike(f"%{normalized_query}%"),
                func.lower(Song.album).ilike(f"%{normalized_query}%"),
                func.lower(Artist.name).ilike(f"%{normalized_query}%")
            )
        )
        .distinct()
        .all()
    )

@app.post("/play/{song_id}")
def increment_play(song_id: str, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    song.play_count += 1
    db.commit()
    db.refresh(song)

    return {"success": True, "play_count": song.play_count}

@app.get("/trending", response_model=list[SongResponse])
def trending_songs(limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Song)\
        .order_by(Song.play_count.desc())\
        .limit(limit)\
        .all()

@app.get("/recent", response_model=list[SongResponse])
def recently_added(limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Song)\
        .order_by(Song.created_at.desc())\
        .limit(limit)\
        .all()

@app.get("/shuffle", response_model=list[SongResponse])
def shuffle_songs(limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Song)\
        .order_by(func.random())\
        .limit(limit)\
        .all()

@app.get("/artist/{artist_name}", response_model=list[SongResponse])
def songs_by_artist(artist_name: str, db: Session = Depends(get_db)):
    return (
        db.query(Song)
        .join(Song.artists)
        .filter(Artist.name.ilike(f"%{artist_name}%"))
        .all()
    )

@app.get("/album/{album_name}", response_model=list[SongResponse])
def songs_by_album(album_name: str, db: Session = Depends(get_db)):
    return db.query(Song)\
        .filter(Song.album.ilike(f"%{album_name}%"))\
        .all()

@app.get("/artists")
def get_artists(db: Session = Depends(get_db)):
    artists = db.query(Artist).order_by(Artist.name.asc()).all()

    return {
        "success": True,
        "count": len(artists),
        "results": [
            {
                "id": artist.id,
                "name": artist.name
            }
            for artist in artists
        ]
    }

@app.get("/albums")
def get_albums(db: Session = Depends(get_db)):
    albums = (
        db.query(Song.album)
        .filter(Song.album.isnot(None))
        .distinct()
        .order_by(Song.album.asc())
        .all()
    )

    return {
        "success": True,
        "count": len(albums),
        "results": [album[0] for album in albums]
    }

@app.get("/artist-image/{artist_name}")
def get_artist_image(artist_name: str):

    DEFAULT_IMAGE = (
        "https://global.honda/en/RandD/assets/img/member/member_ninomiya.jpg"
    )

    try:

        url = (
            f"https://api.deezer.com/search/artist?q="
            f"{artist_name}"
        )

        response = requests.get(url, timeout=10)

        data = response.json()

        artists = data.get("data", [])

        if not artists:
            return {
                "image_url": DEFAULT_IMAGE
            }

        selected_artist = None

        for artist in artists:

            if artist["name"].lower() == artist_name.lower():
                selected_artist = artist
                break

        if not selected_artist:
            selected_artist = artists[0]

        return {
            "artist_used": selected_artist["name"],
            "image_url": (
                selected_artist.get("picture_xl")
                or selected_artist.get("picture_big")
                or selected_artist.get("picture_medium")
                or DEFAULT_IMAGE
            )
        }

    except Exception as e:

        print("Deezer artist image error:", e)

        return {
            "image_url": DEFAULT_IMAGE
        }