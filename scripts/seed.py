"""
Seed script for the booking platform.

Creates:
  - 1 demo user (demo@pvr.local)
  - 3 cities, 3 cinemas each
  - 3 screens per cinema, ~230 seats each
  - 8 movies with genre
  - Showtimes for today + next 7 days, city-aware

Idempotent: safe to re-run.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from passlib.context import CryptContext
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.movie.models import (
    Venue,
    Screen,
    ScreenRow,
    Seat,
    Movie,
    Showtime,
)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_EMAIL = "demo@pvr.local"
DEMO_PASSWORD = "demo1234"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROW_CONFIGS: list[tuple[str, int, int]] = [
    ("A", 20, 19_000),
    ("B", 20, 19_000),
    ("C", 20, 19_000),
    ("D", 22, 29_000),
    ("E", 22, 29_000),
    ("F", 22, 29_000),
    ("G", 26, 39_000),
    ("H", 26, 39_000),
    ("I", 28, 39_000),
    ("J", 28, 39_000),
]

CITIES: dict[str, list[dict]] = {
    "Kochi": [
        {"name": "PVR Lulu Mall", "address": "Lulu Mall, Edappally, Kochi", "screens": 3},
        {"name": "AGS Cinemas",   "address": "Marine Drive, Kochi",         "screens": 3},
        {"name": "Shenoys",       "address": "M.G. Road, Kochi",            "screens": 3},
    ],
    "Chennai": [
        {"name": "PVR Grand Mall",  "address": "Velachery, Chennai",  "screens": 3},
        {"name": "AGS Cinemas",     "address": "OMR, Chennai",        "screens": 3},
        {"name": "Sathyam Cinemas", "address": "Royapettah, Chennai", "screens": 3},
    ],
    "Bangalore": [
        {"name": "PVR Forum Mall",   "address": "Koramangala, Bangalore",  "screens": 3},
        {"name": "INOX Garuda Mall", "address": "Magrath Road, Bangalore", "screens": 3},
        {"name": "Cinepolis Nexus",  "address": "Koramangala, Bangalore",  "screens": 3},
    ],
}

MOVIES: list[dict] = [
    {
        "title": "I Am Game",
        "duration_min": 162,
        "language": "Malayalam",
        "certificate": "UA",
        "genre": "Action, Thriller",
        "release_year": 2025,
        "poster_url": "https://i.pinimg.com/1200x/c7/a8/58/c7a858e124a8da21b34624689fae49b2.jpg",
        "times": [time(15, 30), time(19, 0), time(22, 15)],
    },
    {
        "title": "The Final Whistle",
        "duration_min": 120,
        "language": "English",
        "certificate": "UA",
        "genre": "Drama, Sport",
        "release_year": 2025,
        "poster_url": "https://i.pinimg.com/736x/b2/a3/18/b2a31878a8498a21aa582d78094f775c.jpg",
        "times": [time(14, 0), time(17, 30), time(21, 0)],
    },
    {
        "title": "Manjummel Boys",
        "duration_min": 135,
        "language": "Malayalam",
        "certificate": "UA",
        "genre": "Thriller, Drama",
        "release_year": 2024,
        "poster_url": "https://i.pinimg.com/736x/07/54/ca/0754ca05f3c520d77466af5ccb8c8817.jpg",
        "times": [time(11, 0), time(15, 0), time(19, 30)],
    },
    {
        "title": "Aavesham",
        "duration_min": 155,
        "language": "Malayalam",
        "certificate": "UA",
        "genre": "Action, Comedy",
        "release_year": 2024,
        "poster_url": "https://i.pinimg.com/736x/3f/ff/d7/3fffd702d48852ede79ed71d04f36a2b.jpg",
        "times": [time(12, 30), time(16, 45), time(20, 15)],
    },
    {
        "title": "Kingdom",
        "duration_min": 148,
        "language": "Malayalam",
        "certificate": "UA",
        "genre": "Action, Drama",
        "release_year": 2025,
        "poster_url": "https://i.pinimg.com/736x/33/43/3d/33433d63732e0e1222ae3534bf6495f9.jpg",
        "times": [time(10, 30), time(14, 30), time(18, 30)],
    },
    {
        "title": "Bramayugam",
        "duration_min": 140,
        "language": "Malayalam",
        "certificate": "UA",
        "genre": "Horror, Thriller",
        "release_year": 2024,
        "poster_url": "https://i.pinimg.com/736x/a9/6c/8e/a96c8ee5b797bc99ca40b76e2bc3c3da.jpg",
        "times": [time(13, 15), time(17, 15), time(21, 30)],
    },
    {
        "title": "Vaazha",
        "duration_min": 130,
        "language": "Malayalam",
        "certificate": "U",
        "genre": "Comedy, Drama",
        "release_year": 2025,
        "poster_url": "https://i.pinimg.com/736x/38/20/ae/3820ae353bfc17219ef90810ab47c5b4.jpg",
        "times": [time(11, 45), time(16, 0), time(20, 45)],
    },
    {
        "title": "Avengers: Endgame Encore",
        "duration_min": 182,
        "language": "English",
        "certificate": "UA",
        "genre": "Action, Sci-Fi, Adventure",
        "release_year": 2025,
        "poster_url": "https://i.pinimg.com/736x/93/54/5f/93545f7e45707c04baf5a972efbcbc02.jpg",
        "times": [time(10, 0), time(14, 0), time(18, 30), time(22, 0)],
    },
]

# Which movies play in which city.
# Kochi and Bangalore get the full Malayalam slate + Avengers.
# Chennai gets the pan-India titles only.
MOVIE_AVAILABILITY: dict[str, list[str]] = {
    "Kochi": [
        "I Am Game",
        "The Final Whistle",
        "Manjummel Boys",
        "Aavesham",
        "Kingdom",
        "Bramayugam",
        "Vaazha",
        "Avengers: Endgame Encore",
    ],
    "Chennai": [
        "I Am Game",
        "The Final Whistle",
        "Kingdom",
        "Avengers: Endgame Encore",
    ],
    "Bangalore": [
        "Manjummel Boys",
        "Aavesham",
        "Vaazha",
        "Avengers: Endgame Encore",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_sync_url(async_url: str) -> str:
    sync_url = async_url.replace("+aiosqlite", "").replace("+asyncpg", "")
    if "ssl=require" in sync_url:
        sync_url = sync_url.replace("ssl=require", "sslmode=require")
    return sync_url


def _ensure_venue(s: Session, name: str, city: str, address: str) -> Venue:
    venue = s.execute(
        select(Venue).where(Venue.name == name, Venue.city == city)
    ).scalar_one_or_none()
    if venue:
        return venue

    venue = Venue(
        id=uuid.uuid4(),
        name=name,
        city=city,
        address=address,
        timezone="Asia/Kolkata",
    )
    s.add(venue)
    s.flush()
    return venue


def _ensure_screen(s: Session, venue_id: uuid.UUID, name: str) -> Screen:
    screen = s.execute(
        select(Screen).where(Screen.venue_id == venue_id, Screen.name == name)
    ).scalar_one_or_none()
    if screen:
        return screen

    total_seats = sum(r[1] for r in ROW_CONFIGS)
    screen = Screen(
        id=uuid.uuid4(),
        venue_id=venue_id,
        name=name,
        total_seats=total_seats,
    )
    s.add(screen)
    s.flush()
    return screen


def _ensure_rows_and_seats(s: Session, screen_id: uuid.UUID) -> None:
    for label, seat_count, price_paise in ROW_CONFIGS:
        row = s.execute(
            select(ScreenRow).where(
                ScreenRow.screen_id == screen_id, ScreenRow.label == label
            )
        ).scalar_one_or_none()
        if not row:
            row = ScreenRow(
                id=uuid.uuid4(),
                screen_id=screen_id,
                label=label,
                seat_count=seat_count,
                price_paise=price_paise,
            )
            s.add(row)
            s.flush()

        existing = s.execute(
            select(func.count()).select_from(Seat).where(Seat.row_id == row.id)
        ).scalar()
        if existing == 0:
            for num in range(1, seat_count + 1):
                s.add(
                    Seat(
                        id=uuid.uuid4(),
                        row_id=row.id,
                        number=num,
                        code=f"{label}{num:02d}",
                    )
                )
            s.flush()


def _ensure_movie(s: Session, spec: dict) -> Movie:
    movie = s.execute(
        select(Movie).where(Movie.title == spec["title"])
    ).scalar_one_or_none()
    if movie:
        movie.poster_url = spec["poster_url"]
        movie.genre = spec.get("genre")
        s.flush()
        return movie

    movie = Movie(
        id=uuid.uuid4(),
        title=spec["title"],
        language=spec["language"],
        duration_min=spec["duration_min"],
        certificate=spec["certificate"],
        release_year=spec["release_year"],
        genre=spec.get("genre"),
        poster_url=spec["poster_url"],
        synopsis=f"{spec['title']} — now showing.",
        status="PUBLISHED",
    )
    s.add(movie)
    s.flush()
    return movie


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed(db_url: str | None = None) -> None:
    url = _to_sync_url(db_url or settings.DATABASE_URL)
    engine = create_engine(url)

    with Session(engine) as s:
        # 1. Demo user
        user = s.execute(
            select(User).where(User.email == DEMO_EMAIL)
        ).scalar_one_or_none()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=DEMO_EMAIL,
                password_hash=pwd.hash(DEMO_PASSWORD),
                role="customer",
            )
            s.add(user)
            s.flush()

        # 2. Movies (global — created once)
        movies_by_title: dict[str, Movie] = {}
        for spec in MOVIES:
            movies_by_title[spec["title"]] = _ensure_movie(s, spec)

        total_screens = 0
        total_showtimes = 0

        tz = ZoneInfo("Asia/Kolkata")
        today = datetime.now(tz).date()

        # 3. Cities → venues → screens → showtimes
        for city, venues in CITIES.items():
            available_titles = MOVIE_AVAILABILITY.get(city, [])
            available_specs = [m for m in MOVIES if m["title"] in available_titles]

            if not available_specs:
                continue

            for venue_spec in venues:
                venue = _ensure_venue(
                    s,
                    venue_spec["name"],
                    city,
                    venue_spec["address"],
                )

                for screen_idx in range(venue_spec["screens"]):
                    screen_name = f"Screen {screen_idx + 1}"
                    screen = _ensure_screen(s, venue.id, screen_name)
                    _ensure_rows_and_seats(s, screen.id)
                    total_screens += 1

                    # Assign a rotating subset of city movies to this screen,
                    # so each screen in the venue has a distinct lineup.
                    assigned = [
                        available_specs[(screen_idx + i) % len(available_specs)]
                        for i in range(min(3, len(available_specs)))
                    ]

                    for day_offset in range(8):
                        target_date = today + timedelta(days=day_offset)

                        for spec in assigned:
                            movie_obj = movies_by_title[spec["title"]]
                            for t in spec["times"][:2]:  # 2 shows/day/movie/screen
                                local_dt = datetime.combine(target_date, t, tzinfo=tz)
                                utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

                                st = s.execute(
                                    select(Showtime).where(
                                        Showtime.screen_id == screen.id,
                                        Showtime.starts_at == utc_dt,
                                    )
                                ).scalar_one_or_none()
                                if not st:
                                    s.add(
                                        Showtime(
                                            id=uuid.uuid4(),
                                            screen_id=screen.id,
                                            movie_id=movie_obj.id,
                                            starts_at=utc_dt,
                                        )
                                    )
                                    total_showtimes += 1

        s.commit()

    print(
        f"Seeded: 1 user, {sum(len(v) for v in CITIES.values())} venues "
        f"across {len(CITIES)} cities, {total_screens} screens, "
        f"{len(MOVIES)} movies, {total_showtimes} showtimes."
    )


if __name__ == "__main__":
    seed(sys.argv[1] if len(sys.argv) > 1 else None)