from __future__ import annotations

import sys
import uuid
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from passlib.context import CryptContext
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.movie.models import (
    Cinema,
    Movie,
    Screen,
    ScreenRow,
    Seat,
    Showtime,
    User,
)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

# Each movie gets its own screen -> own showtimes, no collisions.
MOVIES: list[dict] = [
    {
        "title": "I Am Game",
        "duration_min": 162,
        "language": "Malayalam",
        "certificate": "UA",
        "release_year": 2025,
        "poster_url": "https://i.pinimg.com/1200x/c7/a8/58/c7a858e124a8da21b34624689fae49b2.jpg",
        "times": [time(15, 30), time(19, 0), time(22, 15)],
    },
    {
        "title": "The Final Whistle",
        "duration_min": 120,
        "language": "English",
        "certificate": "UA",
        "release_year": 2025,
        "poster_url": "https://i.pinimg.com/736x/b2/a3/18/b2a31878a8498a21aa582d78094f775c.jpg",
        "times": [time(14, 0), time(17, 30), time(21, 0)],
    },
    {
        "title": "Manjummel Boys",
        "duration_min": 135,
        "language": "Malayalam",
        "certificate": "UA",
        "release_year": 2024,
        "poster_url": "https://i.pinimg.com/736x/1a/0c/89/1a0c89e0a6b1e4d3f0a2b0d5c9c6f8e1.jpg",
        "times": [time(11, 0), time(15, 0), time(19, 30)],
    },
    {
        "title": "Aavesham",
        "duration_min": 155,
        "language": "Malayalam",
        "certificate": "UA",
        "release_year": 2024,
        "poster_url": "https://i.pinimg.com/736x/2b/1d/9a/2b1d9a1f7c4e6b3a8d0f2c4e6b3a8d0f.jpg",
        "times": [time(12, 30), time(16, 45), time(20, 15)],
    },
    {
        "title": "Kingdom",
        "duration_min": 148,
        "language": "Malayalam",
        "certificate": "UA",
        "release_year": 2025,
        "poster_url": "https://i.pinimg.com/736x/3c/2e/8b/3c2e8b6d1a5f9c7e3b0d6f9c1a5f9c7e.jpg",
        "times": [time(10, 30), time(14, 30), time(18, 30)],
    },
    {
        "title": "Bramayugam",
        "duration_min": 140,
        "language": "Malayalam",
        "certificate": "UA",
        "release_year": 2024,
        "poster_url": "https://i.pinimg.com/736x/4d/3f/7c/4d3f7c5e2b6a8d0f4c7e2b6a8d0f4c7e.jpg",
        "times": [time(13, 15), time(17, 15), time(21, 30)],
    },
    {
        "title": "Vaazha",
        "duration_min": 130,
        "language": "Malayalam",
        "certificate": "U",
        "release_year": 2025,
        "poster_url": "https://i.pinimg.com/736x/5e/4a/6d/5e4a6d3f8c1b7e2a9d4f8c1b7e2a9d4f.jpg",
        "times": [time(11, 45), time(16, 0), time(20, 45)],
    },
]


def _to_sync_url(async_url: str) -> str:
    sync_url = (
        async_url.replace("+aiosqlite", "")
        .replace("+asyncpg", "")
    )
    if "ssl=require" in sync_url:
        sync_url = sync_url.replace("ssl=require", "sslmode=require")
    return sync_url


def seed(db_url: str | None = None) -> None:
    url = _to_sync_url(db_url or settings.DATABASE_URL)
    engine = create_engine(url)

    with Session(engine) as s:
        # 1. User
        user = s.execute(
            select(User).where(User.email == "demo@pvr.local")
        ).scalar_one_or_none()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="demo@pvr.local",
                password_hash=pwd.hash("demo1234"),
                role="customer",
            )
            s.add(user)
            s.flush()

        # 2. Cinema
        cinema = s.execute(
            select(Cinema).where(Cinema.name == "PVR Lulu Mall")
        ).scalar_one_or_none()
        if not cinema:
            cinema = Cinema(
                id=uuid.uuid4(),
                name="PVR Lulu Mall",
                city="Kochi",
                timezone="Asia/Kolkata",
            )
            s.add(cinema)
            s.flush()

        # 3. Screens & Seats — one screen per movie
        screen_names = [f"Screen {i + 1}" for i in range(len(MOVIES))]
        screens_dict = {}
        for screen_name in screen_names:
            scr = s.execute(
                select(Screen).where(
                    Screen.cinema_id == cinema.id,
                    Screen.name == screen_name,
                )
            ).scalar_one_or_none()
            if not scr:
                scr = Screen(
                    id=uuid.uuid4(), cinema_id=cinema.id, name=screen_name
                )
                s.add(scr)
                s.flush()
            screens_dict[screen_name] = scr

            for label, seat_count, price_cents in ROW_CONFIGS:
                row = s.execute(
                    select(ScreenRow).where(
                        ScreenRow.screen_id == scr.id,
                        ScreenRow.label == label,
                    )
                ).scalar_one_or_none()
                if not row:
                    row = ScreenRow(
                        id=uuid.uuid4(),
                        screen_id=scr.id,
                        label=label,
                        seat_count=seat_count,
                        price_cents=price_cents,
                    )
                    s.add(row)
                    s.flush()

                existing_seats = s.execute(
                    select(func.count())
                    .select_from(Seat)
                    .where(Seat.row_id == row.id)
                ).scalar()
                if existing_seats == 0:
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

        # 4. Movies
        movie_objs: list[Movie] = []
        for spec in MOVIES:
            m = s.execute(
                select(Movie).where(Movie.title == spec["title"])
            ).scalar_one_or_none()
            if not m:
                m = Movie(
                    id=uuid.uuid4(),
                    title=spec["title"],
                    duration_min=spec["duration_min"],
                    language=spec["language"],
                    certificate=spec["certificate"],
                    release_year=spec["release_year"],
                    poster_url=spec["poster_url"],
                )
                s.add(m)
                s.flush()
            else:
                m.poster_url = spec["poster_url"]
            movie_objs.append(m)

        # 5. Seed Showtimes for Today and the Next 7 Days
        tz = ZoneInfo(cinema.timezone)
        today = datetime.now(tz).date()

        for day_offset in range(8):  # Today + next 7 days
            target_date = today + timedelta(days=day_offset)

            for spec, movie_obj, screen_name in zip(MOVIES, movie_objs, screen_names):
                screen = screens_dict[screen_name]
                for t in spec["times"]:
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

        s.commit()

    print(
        f"Seeded successfully: {len(MOVIES)} Screens, "
        f"{len(MOVIES) * sum(r[1] for r in ROW_CONFIGS)} Seats, "
        f"{len(MOVIES)} Movies, showtimes for next 7 days."
    )


if __name__ == "__main__":
    seed(sys.argv[1] if len(sys.argv) > 1 else None)