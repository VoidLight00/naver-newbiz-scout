"""SQLite 데이터베이스 — 누적 방식 업체 관리

first_seen_date: 이 크롤러가 처음 발견한 날짜 (진짜 신규 판별 기준)
last_seen_date:  마지막으로 크롤링에 나타난 날짜
"""

import csv
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from config import CSV_EXPORT_DIR, DB_PATH, NEW_DAYS_THRESHOLD

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS places (
    place_id       TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    category       TEXT,
    address        TEXT,
    phone          TEXT,
    review_count   INTEGER DEFAULT 0,
    rating         REAL DEFAULT 0.0,
    naver_url      TEXT,
    district       TEXT,
    is_new_open    INTEGER DEFAULT 1,
    first_seen_date TEXT NOT NULL,
    last_seen_date  TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_first_seen ON places(first_seen_date);
CREATE INDEX IF NOT EXISTS idx_district   ON places(district);
CREATE INDEX IF NOT EXISTS idx_new_open   ON places(is_new_open);
"""


@dataclass
class Place:
    place_id: str
    name: str
    category: str
    address: str
    phone: str
    review_count: int
    rating: float
    naver_url: str
    district: str
    is_new_open: bool
    first_seen_date: str
    last_seen_date: str


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as conn:
        conn.executescript(CREATE_TABLE + CREATE_INDEX)
    logger.info(f"DB 초기화 완료: {DB_PATH}")


def upsert_place(data: dict) -> bool:
    """업체 upsert. 신규이면 True 반환."""
    now = datetime.now().isoformat()
    today = date.today().isoformat()

    with _conn() as conn:
        existing = conn.execute(
            "SELECT place_id FROM places WHERE place_id = ?", (data["place_id"],)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE places
                   SET review_count = ?, rating = ?, is_new_open = ?,
                       last_seen_date = ?, updated_at = ?
                 WHERE place_id = ?""",
                (
                    data["review_count"],
                    data.get("rating", 0.0),
                    int(data.get("is_new_open", True)),
                    today,
                    now,
                    data["place_id"],
                ),
            )
            return False

        conn.execute(
            """INSERT INTO places
               (place_id, name, category, address, phone,
                review_count, rating, naver_url, district, is_new_open,
                first_seen_date, last_seen_date, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["place_id"],
                data["name"],
                data.get("category", ""),
                data.get("address", ""),
                data.get("phone", ""),
                data.get("review_count", 0),
                data.get("rating", 0.0),
                data.get("naver_url", ""),
                data.get("district", ""),
                int(data.get("is_new_open", True)),
                today,
                today,
                now,
                now,
            ),
        )
        logger.info(f"  [NEW] {data['name']} ({data.get('district', '')})")
        return True


def get_new_today(days: int | None = None) -> list[Place]:
    """최근 N일 이내에 처음 발견된 업체 목록."""
    threshold = days if days is not None else NEW_DAYS_THRESHOLD
    cutoff = (date.today() - timedelta(days=threshold)).isoformat()

    with _conn() as conn:
        rows = conn.execute(
            """SELECT place_id, name, category, address, phone,
                      review_count, rating, naver_url, district, is_new_open,
                      first_seen_date, last_seen_date
                 FROM places
                WHERE first_seen_date >= ?
             ORDER BY first_seen_date DESC, district""",
            (cutoff,),
        ).fetchall()

    return [
        Place(
            place_id=r[0], name=r[1], category=r[2], address=r[3],
            phone=r[4], review_count=r[5], rating=r[6], naver_url=r[7],
            district=r[8], is_new_open=bool(r[9]),
            first_seen_date=r[10], last_seen_date=r[11],
        )
        for r in rows
    ]


def get_all_places() -> list[Place]:
    with _conn() as conn:
        rows = conn.execute(
            """SELECT place_id, name, category, address, phone,
                      review_count, rating, naver_url, district, is_new_open,
                      first_seen_date, last_seen_date
                 FROM places
             ORDER BY first_seen_date DESC"""
        ).fetchall()

    return [
        Place(
            place_id=r[0], name=r[1], category=r[2], address=r[3],
            phone=r[4], review_count=r[5], rating=r[6], naver_url=r[7],
            district=r[8], is_new_open=bool(r[9]),
            first_seen_date=r[10], last_seen_date=r[11],
        )
        for r in rows
    ]


def get_stats() -> dict:
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        today_count = conn.execute(
            "SELECT COUNT(*) FROM places WHERE first_seen_date = ?",
            (date.today().isoformat(),),
        ).fetchone()[0]
        districts = conn.execute(
            "SELECT district, COUNT(*) FROM places GROUP BY district ORDER BY COUNT(*) DESC"
        ).fetchall()

    return {
        "total": total,
        "today": today_count,
        "by_district": {d: c for d, c in districts},
    }


def export_csv(filename: str | None = None):
    os.makedirs(CSV_EXPORT_DIR, exist_ok=True)
    if filename is None:
        filename = f"newbiz_{date.today().isoformat()}.csv"
    filepath = os.path.join(CSV_EXPORT_DIR, filename)

    places = get_all_places()
    if not places:
        logger.info("내보낼 데이터가 없습니다.")
        return

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "place_id", "name", "category", "address", "phone",
            "review_count", "rating", "naver_url", "district",
            "is_new_open", "first_seen_date", "last_seen_date",
        ])
        for p in places:
            writer.writerow([
                p.place_id, p.name, p.category, p.address, p.phone,
                p.review_count, p.rating, p.naver_url, p.district,
                p.is_new_open, p.first_seen_date, p.last_seen_date,
            ])

    logger.info(f"CSV 내보내기 완료: {filepath} ({len(places)}건)")
