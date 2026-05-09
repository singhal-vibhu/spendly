import sqlite3
import os
import sys

# Import get_db from database.db
sys.path.append(os.path.abspath('.'))
from database.db import get_db

def search_user(query):
    try:
        conn = get_db()
        # Case-insensitive partial match for name or email
        sql = "SELECT id, name, email FROM users WHERE name LIKE ? OR email LIKE ?"
        search_pattern = f"%{query}%"
        rows = conn.execute(sql, (search_pattern, search_pattern)).fetchall()
        conn.close()

        print(f"FOUND:{len(rows)}")
        for row in rows:
            print(f"ROW:id={row['id']}|name={row['name']}|email={row['email']}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_user.py <query>")
        sys.exit(1)
    search_user(sys.argv[1])
