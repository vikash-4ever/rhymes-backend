from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from database import SessionLocal, engine
from models import Base, Song, Artist
from schemas import SongResponse
from typing import List
from bs4 import BeautifulSoup
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

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        # -----------------------------
        # normalize variations
        # -----------------------------
        variations = list(set([
            artist_name,

            artist_name.replace("-", "–"),
            artist_name.replace("–", "-"),
            artist_name.replace("—", "-"),

            artist_name.replace("&", "and"),
            artist_name.replace("and", "&"),

            artist_name.replace(".", ""),
        ]))

        # -----------------------------
        # helper
        # -----------------------------
        def extract_image(page_url: str):

            response = requests.get(page_url, headers=headers)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # find ALL image tags
            images = soup.find_all("img")

            for img in images:

                src = (
                    img.get("src")
                    or img.get("data-src")
                    or img.get("data-original")
                )

                if not src:
                    continue

                # ignore placeholder image
                if "2a96cbd8b46e442fc41c2b86b821562f" in src:
                    continue

                # valid lastfm image
                if "lastfm.freetls.fastly.net" in src:

                    # upgrade quality
                    src = (
                        src
                        .replace("avatar170s", "770x0")
                        .replace("300x300", "770x0")
                    )

                    return src

            return None

        # -----------------------------
        # direct attempts
        # -----------------------------
        for name in variations:

            print("Trying direct:", name)

            url = (
                f"https://www.last.fm/music/"
                f"{name.replace(' ', '+')}/+images"
            )

            image_url = extract_image(url)

            if image_url:

                return {
                    "artist_used": name,
                    "image_url": image_url
                }

        # -----------------------------
        # fallback search
        # -----------------------------
        print("Trying search:", artist_name)

        search_url = (
            f"https://www.last.fm/search/artists?q="
            f"{artist_name.replace(' ', '+')}"
        )

        search_response = requests.get(search_url, headers=headers)

        if search_response.status_code != 200:
            return {"image_url": None}

        search_soup = BeautifulSoup(search_response.text, "html.parser")

        artist_href = None

        for a in search_soup.find_all("a", href=True):

            href = a.get("href")

            if href and href.startswith("/music/"):

                # ignore unrelated links
                if "/+wiki" in href:
                    continue

                artist_href = href
                break

        if not artist_href:
            return {"image_url": None}

        print("Matched href:", artist_href)

        artist_page = f"https://www.last.fm{artist_href}/+images"

        print("Matched artist page:", artist_page)

        image_url = extract_image(artist_page)

        if image_url:

            return {
                "artist_used": artist_href.split("/")[-1],
                "image_url": image_url
            }

        return {"image_url": None}

    except Exception as e:
        print("Artist image scrape error:", e)
        return {"image_url": None}