import json
from database import SessionLocal, engine
from models import Base, Song, Artist
from datetime import datetime
import uuid

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Load JSON
with open("final_songs.json", "r", encoding="utf-8") as f:
    songs_data = json.load(f)

for item in songs_data:
    print(f"Inserting: {item['title']}")

    # Check if song already exists
    existing_song = db.query(Song).filter_by(id=item["id"]).first()
    if existing_song:
        print("   ⏭ Skipped (already exists)")
        continue

    # Create Song
    song = Song(
        id=item["id"],
        title=item["title"],
        album=item.get("album"),
        genre=item.get("genre"),
        duration_seconds=item.get("duration_seconds"),
        audio_url=item.get("audioUrl") or item.get("audio_url"),
        thumbnail_url=item.get("thumbnailUrl") or item.get("thumbnail_url"),
        lyrics_url=item.get("lyricsUrl") or item.get("lyrics_url"),
        play_count=item.get("playCount", 0),
        created_at=datetime.fromisoformat(
            item["createdAt"].replace("Z", "+00:00")
        ) if item.get("createdAt") else datetime.utcnow()
    )

    db.add(song)

    # Normalize Artists
    artist_names = item["artist"].split(",")

    for name in artist_names:
        clean_name = name.strip()

        artist = db.query(Artist).filter_by(name=clean_name).first()

        if not artist:
            artist = Artist(
                id=str(uuid.uuid4()),
                name=clean_name
            )
            db.add(artist)
        song.artists.append(artist)
    db.flush()  # important so artist gets ID
db.commit()
db.close()

print("\n🎉 Seeding Complete.")