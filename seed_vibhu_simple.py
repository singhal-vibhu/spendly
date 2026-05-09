import random
from database.db import get_db, create_user, get_user_by_email

def generate_vibhu_no_last_name():
    name = "Vibhu"
    # Derived email from the name "Vibhu" with a random 2-3 digit suffix
    email_prefix = name.lower()
    email = f"{email_prefix}{random.randint(10, 999)}@gmail.com"
    return name, email

def seed_vibhu_user():
    while True:
        name, email = generate_vibhu_no_last_name()
        if not get_user_by_email(email):
            break

    # Use the create_user helper from db.py which handles password hashing
    user_id = create_user(name, email, "1234")

    print(f"User created successfully:")
    print(f"ID: {user_id}")
    print(f"Name: {name}")
    print(f"Email: {email}")

if __name__ == "__main__":
    seed_vibhu_user()
