import random
from database.db import get_db, create_user, get_user_by_email

def generate_indian_user():
    first_names = ["Aarav", "Vihaan", "Aditya", "Arjun", "Sai", "Ishaan", "Ananya", "Diya", "Myra", "Saanvi"]
    last_names = ["Sharma", "Verma", "Gupta", "Iyer", "Reddy", "Patel", "Singh", "Chatterjee", "Nair", "Kulkarni"]

    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    email_prefix = name.lower().replace(" ", ".")
    email = f"{email_prefix}{random.randint(10, 999)}@gmail.com"

    return name, email

def seed_random_user():
    while True:
        name, email = generate_indian_user()
        if not get_user_by_email(email):
            break

    # Use the create_user helper from db.py which handles password hashing
    user_id = create_user(name, email, "1234")

    print(f"User created successfully:")
    print(f"ID: {user_id}")
    print(f"Name: {name}")
    print(f"Email: {email}")

if __name__ == "__main__":
    seed_random_user()
