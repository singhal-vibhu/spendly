import sqlite3
import os
import sys

# Import get_db from database.db
sys.path.append(os.path.abspath('.'))
from database.db import get_db

def delete_user(user_id):
    try:
        conn = get_db()
        # Fetch user details before deletion for the success message
        user = conn.execute("SELECT name, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            print(f"Error: User with ID {user_id} not found.")
            sys.exit(1)

        name = user['name']
        email = user['email']

        # Delete the user
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        print("User deleted successfully.\n")
        print(f"    ID:    {user_id}")
        print(f"    Name:  {name}")
        print(f"    Email: {email}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Hardcoding the selected ID 7
    delete_user(7)
