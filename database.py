import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "literary_viz.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            genre TEXT,
            sentence_count INTEGER,
            analyzed_at TEXT,
            peak_part INTEGER,
            peak_sentences TEXT,
            valence TEXT,
            tension TEXT,
            parts TEXT,
            characters TEXT,
            character_focus TEXT,
            locations TEXT,
            structure TEXT,
            summary TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized.")


def _strip_parts(parts: list, peak_part: int) -> list:
    stripped = []
    for p in parts:
        part_data = {
            "part": p["part"],
            "sent_range": p["sent_range"],
            "dominant_emotion": p["dominant_emotion"],
            "emotion_dist": p["emotion_dist"],
            "spike": p["spike"],
            "turn": p["turn"],
        }
        if p["part"] == peak_part:
            part_data["sentences"] = p.get("sentences", [])
        else:
            part_data["sentences"] = []
        stripped.append(part_data)
    return stripped


def save_analysis(result: dict) -> int:
    conn = get_connection()

    peak_part = result.get("peak_part", 1)
    parts = result.get("parts", [])
    stripped_parts = _strip_parts(parts, peak_part)

    peak_sentences = []
    for p in parts:
        if p["part"] == peak_part:
            peak_sentences = p.get("sentences", [])
            break

    existing = conn.execute(
        "SELECT id, author FROM books WHERE LOWER(title) = LOWER(?)",
        (result["title"],)
    ).fetchone()

    data = (
        result["title"],
        result["author"],
        result["genre"],
        len(result.get("sentences", [])),
        datetime.now().isoformat(),
        peak_part,
        json.dumps(peak_sentences),
        json.dumps(result.get("valence", [])),
        json.dumps(result.get("tension", [])),
        json.dumps(stripped_parts),
        json.dumps(result.get("characters", {})),
        json.dumps(result.get("character_focus", {})),
        json.dumps(result.get("locations", [])),
        json.dumps(result.get("structure", {})),
        result.get("summary", ""),
    )

    if existing:
        book_id = existing["id"]
        old_author = existing["author"]
        if old_author == "Unknown" or result["author"] != "Unknown":
            conn.execute("""
                UPDATE books SET
                    author = ?, genre = ?, sentence_count = ?, analyzed_at = ?,
                    peak_part = ?, peak_sentences = ?, valence = ?, tension = ?,
                    parts = ?, characters = ?, character_focus = ?, locations = ?,
                    structure = ?, summary = ?
                WHERE id = ?
            """, data[1:] + (book_id,))
            print(f"Updated existing book: {result['title']} (id={book_id})")
        else:
            print(f"Book already exists, skipping update: {result['title']}")
    else:
        cursor = conn.execute("""
            INSERT INTO books (
                title, author, genre, sentence_count, analyzed_at,
                peak_part, peak_sentences, valence, tension, parts,
                characters, character_focus, locations, structure, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        book_id = cursor.lastrowid
        print(f"Saved new book: {result['title']} (id={book_id})")

    conn.commit()
    conn.close()
    return book_id


def get_book_by_title(title: str) -> dict:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM books WHERE LOWER(title) = LOWER(?)", (title,)
    ).fetchone()
    conn.close()
    if not row:
        return {}
    book = dict(row)
    for field in ["peak_sentences", "valence", "tension", "parts", "characters", "character_focus", "locations", "structure"]:
        if book.get(field):
            book[field] = json.loads(book[field])
    return book


def get_all_books() -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, title, author, genre, sentence_count, analyzed_at, peak_part, summary
        FROM books
        ORDER BY analyzed_at DESC
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_book(book_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    if not row:
        return {}
    book = dict(row)
    for field in ["peak_sentences", "valence", "tension", "parts", "characters", "character_focus", "locations", "structure"]:
        if book.get(field):
            book[field] = json.loads(book[field])
    return book


def search_books(query: str) -> list:
    conn = get_connection()
    q = f"%{query}%"
    rows = conn.execute("""
        SELECT id, title, author, genre, sentence_count, analyzed_at, summary
        FROM books
        WHERE title LIKE ? OR author LIKE ?
        ORDER BY analyzed_at DESC
    """, (q, q)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_book(book_id: int) -> bool:
    conn = get_connection()
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    print(f"Deleted book id={book_id}")
    return True
