import sqlite3
import sys
from database.db import get_db

def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_user.py <name-or-email> [user_id]")
        sys.exit(1)

    search_term = sys.argv[1]
    conn = get_db()

    # If a second argument is provided and it's a number, treat it as a direct ID delete
    if len(sys.argv) >= 3:
        try:
            target_id = int(sys.argv[2])
            user = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (target_id,)).fetchone()
            if user:
                conn.execute("DELETE FROM users WHERE id = ?", (target_id,))
                conn.commit()
                print(f"\n✓ User deleted successfully.\n")
                print(f"  ID:    {user['id']}")
                print(f"  Name:  {user['name']}")
                print(f"  Email: {user['email']}")
                conn.close()
                return
            else:
                print(f"Error: User with ID {target_id} not found.")
                conn.close()
                sys.exit(1)
        except ValueError:
            print("Error: Second argument must be a numeric User ID for direct deletion.")
            conn.close()
            sys.exit(1)

    # Default interactive flow for discovery
    query = "SELECT id, name, email FROM users WHERE name LIKE ? OR email LIKE ?"
    pattern = f"%{search_term}%"
    users = conn.execute(query, (pattern, pattern)).fetchall()

    if not users:
        print(f'No user found matching "{search_term}". Nothing was deleted.')
        conn.close()
        return

    if len(users) == 1:
        user = users[0]
        print(f"Found 1 user:\n  ID:    {user['id']}\n  Name:  {user['name']}\n  Email: {user['email']}")
        print(f"\nTo delete this user, run: python delete_user.py {search_term} {user['id']}")
    else:
        print(f'Found {len(users)} users matching "{search_term}":\n')
        for i, user in enumerate(users, 1):
            print(f"  [{i}]  ID: {user['id']}  |  Name: {user['name']}  |  Email: {user['email']}")
        print(f"\nTo delete one of these, run: python delete_user.py {search_term} <ID>")

    conn.close()

if __name__ == "__main__":
    main()
