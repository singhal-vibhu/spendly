import random
import sqlite3
from datetime import datetime, timedelta
from database.db import get_db

def seed_expenses(user_id, count, months):
    # Verify user exists
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        print(f"No user found with id {user_id}.")
        conn.close()
        return

    categories = {
        "Food": {"range": (50, 800), "weight": 30, "desc": ["Groceries", "Swiggy", "Zomato", "Dinner at restaurant", "Tea and snacks"]},
        "Transport": {"range": (20, 500), "weight": 20, "desc": ["Auto ride", "Uber", "Ola", "Metro recharge", "Petrol"]},
        "Bills": {"range": (200, 3000), "weight": 15, "desc": ["Electricity bill", "Water bill", "Wifi recharge", "Phone bill"]},
        "Health": {"range": (100, 2000), "weight": 5, "desc": ["Pharmacy", "Doctor consultation", "Lab tests", "Medicines"]},
        "Entertainment": {"range": (100, 1500), "weight": 5, "desc": ["Movie tickets", "Netflix subscription", "Gaming", "Concert"]},
        "Shopping": {"range": (200, 5000), "weight": 15, "desc": ["Amazon purchase", "Flipkart", "Clothes", "Footwear", "Electronics"]},
        "Other": {"range": (50, 1000), "weight": 10, "desc": ["Miscellaneous", "Gift", "Donation", "Parking fee"]}
    }

    cat_list = list(categories.keys())
    weights = [categories[c]["weight"] for c in cat_list]

    expenses = []
    start_date = datetime.now() - timedelta(days=months * 30)

    for _ in range(count):
        cat = random.choices(cat_list, weights=weights)[0]
        amount = round(random.uniform(*categories[cat]["range"]), 2)
        description = random.choice(categories[cat]["desc"])

        # Random date between start_date and now
        random_days = random.randint(0, months * 30)
        date_obj = start_date + timedelta(days=random_days)
        date_str = date_obj.strftime("%Y-%m-%d")

        expenses.append((user_id, amount, cat, date_str, description))

    try:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            expenses
        )
        conn.commit()

        # Get date range
        dates = [e[3] for e in expenses]
        min_date = min(dates)
        max_date = max(dates)

        print(f"Successfully inserted {len(expenses)} expenses.")
        print(f"Date range: {min_date} to {max_date}")
        print("\nSample of 5 records:")

        sample_query = conn.execute(
            "SELECT id, amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY RANDOM() LIMIT 5",
            (user_id,)
        ).fetchall()

        for row in sample_query:
            print(f"ID: {row['id']} | {row['date']} | {row['category']}: ₹{row['amount']} - {row['description']}")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # User input: Vibhu 10 6
    # Based on previous turns, Vibhu's ID might be 7 or 8.
    # However, the prompt says "User input: Vibhu 10 6" but then says "Extract user_id — integer".
    # This is a contradiction in the prompt's example vs its instructions.
    # I will assume "Vibhu" in the arguments was intended to be the ID.
    # Since the prompt specifically asked me to parse "Vibhu 10 6",
    # but "Vibhu" is not an integer, I should strictly follow Step 1.

    # WAIT: The prompt says: "Extract from Vibhu 10 6: user_id — integer".
    # If I try to convert "Vibhu" to int, it will fail.
    # But since I am the agent implementing the skill, I should probably
    # handle the case where the user provided a name instead of an ID,
    # OR strictly follow the error message requirement.
    # Let's try to parse the arguments as requested.

    import sys
    args = "Vibhu 10 6".split()

    try:
        user_id = int(args[0])
        count = int(args[1])
        months = int(args[2])
        seed_expenses(user_id, count, months)
    except (ValueError, IndexError):
        print("Usage: /seed-expenses <user_id> <count> <months>")
        print("Example: /seed-expenses 1 50 6")
