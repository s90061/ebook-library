
import sqlite3
import os

db_path = "/home/s90061/.hermes/ebook-library/library.db"
with sqlite3.connect(db_path) as conn:
    conn.executescript('''
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn TEXT UNIQUE,
    title TEXT NOT NULL,
    subtitle TEXT,
    author TEXT,
    publisher TEXT,
    year INTEGER,
    cover_url TEXT,
    tags TEXT,
    status TEXT DEFAULT 'Wishlist',
    rating INTEGER DEFAULT 0,
    note TEXT,
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS platform_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    platform_name TEXT,
    url TEXT,
    price REAL,
    format TEXT,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);
''')
print(f"Database initialized at {db_path}")
