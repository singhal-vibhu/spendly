import random
from database.db import get_db, create_user, get_user_by_email

def generate_vibhu_user():
    # The user specifically asked for the name "Vibhu"
    first_name = "Vibhu"
    last_names = ["Sharma", "Verma", "Gupta", "Iyer", "Reddy", "Patel", "Singh", "Chatterjee", "Nair", "Kulkarni"]
    last_name = random.choice(last_names)

    name = f"{first_name} {last_name}"
    email_prefix = f"{first_name.lower()}.{last_name.lower()}"
    email = f"{email_prefix}{random.randint(10, 999)}@gmail.com"

    return name, email

def seed_vibhu_user():
    while True:
        name, email = generate_vibhu_user()
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
