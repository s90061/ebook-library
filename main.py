"""
E-Book Library Server - FastAPI Backend
Port: 8086
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import pathlib
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import os
from datetime import datetime

app = FastAPI(title="E-Book Library")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "library.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Ensure directories exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ============== Pydantic Models ==============
class PlatformLink(BaseModel):
    platform_name: str
    url: str
    price: Optional[float] = None
    format: Optional[str] = None

class BookCreate(BaseModel):
    isbn: Optional[str] = None
    title: str
    subtitle: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None
    cover_url: Optional[str] = None
    tags: Optional[str] = None
    status: str = "Wishlist"
    rating: int = 0
    note: Optional[str] = None
    platforms: Optional[List[PlatformLink]] = None

class BookUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None
    cover_url: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = None
    rating: Optional[int] = None
    note: Optional[str] = None

# ============== DB Helpers ==============
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    return dict(row) if row else None

# ============== Routes ==============
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main library UI"""
    index_path = pathlib.Path(TEMPLATES_DIR) / "index.html"
    html = index_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html)

@app.get("/api/css/style.css")
async def css():
    css_path = pathlib.Path(STATIC_DIR) / "css" / "style.css"
    return HTMLResponse(content=css_path.read_text(encoding="utf-8"), media_type="text/css")

@app.get("/api/js/app.js")
async def js():
    js_path = pathlib.Path(STATIC_DIR) / "js" / "app.js"
    return HTMLResponse(content=js_path.read_text(encoding="utf-8"), media_type="application/javascript")

@app.get("/api/books")
async def get_books(status: Optional[str] = None, search: Optional[str] = None):
    """Get all books with optional filtering"""
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM books"
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if search:
        conditions.append("(title LIKE ? OR author LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY date_added DESC"

    cursor.execute(query, params)
    book_rows = cursor.fetchall()

    book_ids = [row["id"] for row in book_rows]
    platforms_by_book = {book_id: [] for book_id in book_ids}
    if book_ids:
        placeholders = ",".join("?" * len(book_ids))
        cursor.execute(
            f"SELECT * FROM platform_links WHERE book_id IN ({placeholders})",
            book_ids,
        )
        for p_row in cursor.fetchall():
            platforms_by_book[p_row["book_id"]].append(dict_from_row(p_row))

    conn.close()

    books = []
    for row in book_rows:
        book = dict_from_row(row)
        book["platforms"] = platforms_by_book[row["id"]]
        books.append(book)

    return {"books": books, "count": len(books)}

@app.get("/api/books/{book_id}")
async def get_book(book_id: int):
    """Get a single book with all details"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book_row = cursor.fetchone()
    
    if not book_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    book = dict_from_row(book_row)
    
    cursor.execute("SELECT * FROM platform_links WHERE book_id = ?", (book_id,))
    platforms = cursor.fetchall()
    book['platforms'] = [dict_from_row(p) for p in platforms]
    
    conn.close()
    return book

@app.post("/api/books")
async def create_book(book_data: BookCreate):
    """Create a new book"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO books (isbn, title, subtitle, author, publisher, year, 
                             cover_url, tags, status, rating, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            book_data.isbn, book_data.title, book_data.subtitle,
            book_data.author, book_data.publisher, book_data.year,
            book_data.cover_url, book_data.tags, book_data.status,
            book_data.rating, book_data.note
        ))
        
        book_id = cursor.lastrowid
        
        # Add platform links if provided
        if book_data.platforms:
            for platform in book_data.platforms:
                cursor.execute("""
                    INSERT INTO platform_links (book_id, platform_name, url, price, format)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    book_id, platform.platform_name, platform.url,
                    platform.price, platform.format
                ))
        
        conn.commit()
        return {"success": True, "book_id": book_id}
    
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"ISBN already exists: {str(e)}")

@app.put("/api/books/{book_id}")
async def update_book(book_id: int, book_data: BookUpdate):
    """Update an existing book"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build dynamic update query
    updates = []
    params = []
    
    for field, value in book_data.model_dump().items():
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(book_id)
    query = f"UPDATE books SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, params)
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    conn.commit()
    conn.close()
    return {"success": True}

@app.delete("/api/books/{book_id}")
async def delete_book(book_id: int):
    """Delete a book"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    conn.commit()
    conn.close()
    return {"success": True}

@app.post("/api/books/{book_id}/platforms")
async def add_platform(book_id: int, platform: PlatformLink):
    """Add a platform link to an existing book"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Book not found")
    
    cursor.execute("""
        INSERT INTO platform_links (book_id, platform_name, url, price, format)
        VALUES (?, ?, ?, ?, ?)
    """, (book_id, platform.platform_name, platform.url, platform.price, platform.format))
    
    conn.commit()
    conn.close()
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8086)