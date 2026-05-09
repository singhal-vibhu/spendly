import sqlite3
from database.db import get_db

def delete_user_workflow(search_term):
    conn = get_db()
    try:
        # Step 1: Search for the user (case-insensitive partial match)
        query = "SELECT id, name, email FROM users WHERE name LIKE ? OR email LIKE ? COLLATE NOCASE"
        pattern = f"%{search_term}%"
        users = conn.execute(query, (pattern, pattern)).fetchall()

        if not users:
            print(f'No user found matching "{search_term}". Nothing was deleted.')
            return

        selected_user = None

        if len(users) == 1:
            # Exactly one user found
            user = users[0]
            print("Found 1 user:")
            print(f"    ID:    {user['id']}")
            print(f"    Name:  {user['name']}")
            print(f"    Email: {user['email']}")

            confirm = input("Confirm delete? [y/N]: ")
            if confirm.lower() == 'y':
                selected_user = user
            else:
                print("Aborted. No changes made.")
                return

        else:
            # Multiple users found
            print(f"Found {len(users)} users matching \"{search_term}\":\n")
            for i, user in enumerate(users, 1):
                print(f"    [{i}]  ID: {user['id']}  |  Name: {user['name']}  |  Email: {user['email']}")
            print("    [0]  Cancel")

            try:
                choice = int(input("\nEnter the number of the user to delete: "))
                if choice == 0 or choice < 1 or choice > len(users):
                    print("Aborted. No changes made.")
                    return

                user = users[choice - 1]
                print("\nYou selected:")
                print(f"    ID:    {user['id']}")
                print(f"    Name:  {user['name']}")
                print(f"    Email: {user['email']}")

                confirm = input("\nConfirm delete? [y/N]: ")
                if confirm.lower() == 'y':
                    selected_user = user
                else:
                    print("Aborted. No changes made.")
                    return
            except ValueError:
                print("Aborted. No changes made.")
                return

        if selected_user:
            # Step 3: Delete the user by ID
            conn.execute("DELETE FROM users WHERE id = ?", (selected_user['id'],))
            conn.commit()

            # Step 4: Confirmation
            print("\n✓ User deleted successfully.")
            print(f"  ID:    {selected_user['id']}")
            print(f"  Name:  {selected_user['name']}")
            print(f"  Email: {selected_user['email']}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # For the purpose of this CLI tool, we'll use the argument provided
    import sys
    search_term = "Vibhu" # Provided argument
    delete_user_workflow(search_term)
