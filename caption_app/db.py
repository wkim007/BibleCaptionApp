from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from caption_app.models import Book, VerseBundle, VerseReference

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "bible.db"


def resolve_db_path() -> Path:
    configured_path = os.environ.get("BIBLEDISK_DB_PATH", "").strip()
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DB_PATH


DB_PATH = resolve_db_path()


class BibleRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or resolve_db_path()
        if not self.db_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.db_path}")

    def list_books(self) -> list[Book]:
        query = """
            SELECT book_id, kor_full, eng_full, chapter_count
            FROM books
            ORDER BY book_id
        """
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(query).fetchall()
        return [Book(row[0], row[1], row[2], row[3]) for row in rows]

    def list_chapters(self, book_id: int) -> list[int]:
        query = "SELECT chapter_count FROM books WHERE book_id = ?"
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(query, (book_id,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown book id: {book_id}")
        return list(range(1, int(row[0]) + 1))

    def list_verses(self, book_id: int, chapter_num: int) -> list[int]:
        query = """
            SELECT verse_num
            FROM verses
            WHERE book_id = ? AND chapter_num = ?
            ORDER BY verse_num
        """
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(query, (book_id, chapter_num)).fetchall()
        return [row[0] for row in rows]

    def get_verse_bundle(self, book_id: int, chapter_num: int, verse_num: int) -> VerseBundle:
        query = """
            SELECT
                b.book_id,
                b.kor_full,
                b.eng_full,
                v.chapter_num,
                v.verse_num,
                MAX(CASE WHEN vt.version_id = 1 THEN vt.verse_text END) AS korean_text,
                MAX(CASE WHEN vt.version_id = 2 THEN vt.verse_text END) AS english_text,
                MAX(CASE WHEN vt.version_id = 3 THEN vt.verse_text END) AS spanish_text
            FROM verses v
            JOIN books b ON b.book_id = v.book_id
            JOIN verse_texts vt ON vt.verse_id = v.verse_id
            WHERE v.book_id = ? AND v.chapter_num = ? AND v.verse_num = ?
            GROUP BY b.book_id, b.kor_full, b.eng_full, v.chapter_num, v.verse_num
        """
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(query, (book_id, chapter_num, verse_num)).fetchone()

        if row is None:
            raise ValueError(f"Verse not found: book={book_id}, chapter={chapter_num}, verse={verse_num}")

        reference = VerseReference(
            book_id=row[0],
            book_korean=row[1],
            book_english=row[2],
            chapter_num=row[3],
            verse_num=row[4],
        )
        return VerseBundle(
            reference=reference,
            korean_text=row[5] or "",
            english_text=row[6] or "",
            spanish_text=row[7] or "",
        )
