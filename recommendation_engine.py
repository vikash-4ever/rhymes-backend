import random
from collections import Counter
from dataclasses import dataclass
from sqlalchemy.orm import Session, selectinload
from models import Song
from operator import attrgetter

@dataclass
class Recommendation:
    song: Song
    score: float


# =========================
# Recommendation Weights
# =========================

ARTIST_WEIGHT = 40
LIKED_ARTIST_WEIGHT = 80
ALBUM_WEIGHT = 20
GENRE_WEIGHT = 10
POPULARITY_WEIGHT = 0.02
RANDOM_WEIGHT = 3


# =========================
# User Taste Profile Weights
# =========================

LIKED_SONG_ARTIST_SCORE = 3
RECENT_SONG_ARTIST_SCORE = 2
LIKED_ARTIST_SCORE = 1

LIKED_SONG_ALBUM_SCORE = 2
RECENT_SONG_ALBUM_SCORE = 1

LIKED_SONG_GENRE_SCORE = 1
RECENT_SONG_GENRE_SCORE = 1

UNKNOWN_GENRE = "Unknown"


def recommend(
    db: Session,
    liked_song_ids: list[str],
    recent_song_ids: list[str],
    liked_artists: list[str],
    limit: int = 20,
):
    
    limit = max(limit, 1)

    liked_songs = (
        db.query(Song)
        .options(selectinload(Song.artists))
        .filter(Song.id.in_(liked_song_ids))
        .all()
    )

    recent_songs = (
        db.query(Song)
        .options(selectinload(Song.artists))
        .filter(Song.id.in_(recent_song_ids))
        .all()
    )

    artist_counter = Counter()
    liked_artist_counter = Counter()
    album_counter = Counter()
    genre_counter = Counter()

    # =========================
    # Build User Profile
    # =========================

    for song in liked_songs:

        for artist in song.artists:
            artist_counter[artist.name] += LIKED_SONG_ARTIST_SCORE

        if song.album:
            album_counter[song.album] += LIKED_SONG_ALBUM_SCORE

        if song.genre and song.genre != UNKNOWN_GENRE:
            genre_counter[song.genre] += LIKED_SONG_GENRE_SCORE

    for song in recent_songs:

        for artist in song.artists:
            artist_counter[artist.name] += RECENT_SONG_ARTIST_SCORE

        if song.album:
            album_counter[song.album] += RECENT_SONG_ALBUM_SCORE

        if song.genre and song.genre != UNKNOWN_GENRE:
            genre_counter[song.genre] += RECENT_SONG_GENRE_SCORE

    for artist in liked_artists:
        liked_artist_counter[artist] += LIKED_ARTIST_SCORE

    # =========================
    # New User Fallback
    # =========================

    if (
        not artist_counter
        and not liked_artist_counter
        and not album_counter
        and not genre_counter
    ):
        return (
            db.query(Song)
            .order_by(Song.play_count.desc())
            .limit(limit)
            .all()
        )

    all_songs = (
        db.query(Song)
        .options(selectinload(Song.artists))
        .all()
    )

    excluded_song_ids = set(liked_song_ids)
    excluded_song_ids.update(recent_song_ids)

    recommendations: list[Recommendation] = []

    # =========================
    # Score Songs
    # =========================

    for song in all_songs:

        if song.id in excluded_song_ids:
            continue

        score = 0.0

        # Artist Match
        for artist in song.artists:

            score += (
                artist_counter.get(artist.name, 0)
                * ARTIST_WEIGHT
            )

            score += (
                liked_artist_counter.get(artist.name, 0)
                * LIKED_ARTIST_WEIGHT
            )

        # Album Match
        if song.album:
            score += (
                album_counter.get(song.album, 0)
                * ALBUM_WEIGHT
            )

        # Genre Match
        if song.genre and song.genre != UNKNOWN_GENRE:
            score += (
                genre_counter.get(song.genre, 0)
                * GENRE_WEIGHT
            )

        # Popularity
        score += song.play_count * POPULARITY_WEIGHT

        # Small Randomness
        score += random.uniform(0, RANDOM_WEIGHT)

        recommendations.append(
            Recommendation(
                song=song,
                score=score,
            )
        )

    # =========================
    # Highest Score First
    # =========================

    recommendations.sort(
        key=attrgetter("score"),
        reverse=True,
    )

    return [
        recommendation.song
        for recommendation in recommendations[:limit]
    ]

