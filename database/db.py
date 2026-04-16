import sqlite3
from werkzeug.security import generate_password_hash

DATABASE_PATH = "spendly.db"


def get_db():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the database tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def seed_db():
    """Insert sample data if not already present."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if users table already has data
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Insert demo user
    password_hash = generate_password_hash("demo123")
    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", password_hash)
    )

    # Get the user_id of the demo user
    cursor.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",))
    user_id = cursor.fetchone()[0]

    # Insert 8 sample expenses across all categories
    # Categories: Food, Transport, Bills, Health, Entertainment, Shopping, Other
    expenses = [
        (15.50, "Food", "2026-04-01", "Lunch at cafe"),
        (25.00, "Transport", "2026-04-03", "Uber ride to airport"),
        (120.00, "Bills", "2026-04-05", "Electric bill"),
        (45.00, "Health", "2026-04-07", "Pharmacy"),
        (30.00, "Entertainment", "2026-04-09", "Movie tickets"),
        (85.00, "Shopping", "2026-04-11", "New shoes"),
        (50.00, "Other", "2026-04-13", "Gift for friend"),
        (12.75, "Food", "2026-04-14", "Breakfast"),
    ]

    for amount, category, date, description in expenses:
        cursor.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description)
        )

    conn.commit()
    conn.close()


def create_user(name, email, password):
    """Create a new user with hashed password.

    Args:
        name: User's display name
        email: User's email (must be unique)
        password: Plain text password to hash

    Returns:
        The new user's id

    Raises:
        sqlite3.IntegrityError: If email already exists
    """
    conn = get_db()
    cursor = conn.cursor()

    password_hash = generate_password_hash(password)

    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash)
    )

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return user_id
