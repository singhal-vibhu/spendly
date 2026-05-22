import pytest
from app import app as flask_app
from database.db import init_db
from database.queries import get_expense_by_id, update_expense

@pytest.fixture
def app(tmp_path):
    db_file = tmp_path / "test_spendly.db"
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': str(db_file),
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })
    with flask_app.app_context():
        init_db()
        yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """A test client logged in as testuser."""
    client.post('/register', data={'name': 'testuser', 'email': 'test@test.com', 'password': 'testpass', 'confirm_password': 'testpass'})
    client.post('/login', data={'email': 'test@test.com', 'password': 'testpass'})
    return client

@pytest.fixture
def auth_client_other(client):
    """A test client logged in as otheruser."""
    client.post('/register', data={'name': 'otheruser', 'email': 'other@test.com', 'password': 'otherpass', 'confirm_password': 'otherpass'})
    client.post('/login', data={'email': 'other@test.com', 'password': 'otherpass'})
    return client

class TestEditExpenseDB:
    def test_get_expense_by_id_valid(self, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            # Create a user first to get a valid ID
            cursor = db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("testuser", "test@test.com", "hash"))
            user_id = cursor.lastrowid

            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

            expense = get_expense_by_id(expense_id, user_id)
            assert expense is not None
            assert expense["id"] == expense_id
            assert expense["amount"] == 100.0
            assert expense["category"] == "Food"

    def test_get_expense_by_id_wrong_user(self, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            # User A owns the expense
            db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("user_a", "a@test.com", "hash"))
            user_a_id = db.execute("SELECT id FROM users WHERE name = 'user_a'").fetchone()[0]

            # User B is the one requesting
            db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("user_b", "b@test.com", "hash"))
            user_b_id = db.execute("SELECT id FROM users WHERE name = 'user_b'").fetchone()[0]

            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

            expense = get_expense_by_id(expense_id, user_b_id)
            assert expense is None

    def test_get_expense_by_id_nonexistent(self, app):
        with app.app_context():
            # user_id 1 might not exist, but get_expense_by_id should return None regardless
            expense = get_expense_by_id(999, 1)
            assert expense is None

    def test_update_expense_valid(self, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("testuser", "test@test.com", "hash"))
            user_id = db.execute("SELECT id FROM users WHERE name = 'testuser'").fetchone()[0]

            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

            update_expense(expense_id, user_id, 150.0, "Shopping", "2026-01-02", "New Shirt")

            row = db.execute("SELECT amount, category, date, description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            assert row["amount"] == 150.0
            assert row["category"] == "Shopping"
            assert row["date"] == "2026-01-02"
            assert row["description"] == "New Shirt"

    def test_update_expense_wrong_user(self, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("user_a", "a@test.com", "hash"))
            user_a_id = db.execute("SELECT id FROM users WHERE name = 'user_a'").fetchone()[0]
            db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("user_b", "b@test.com", "hash"))
            user_b_id = db.execute("SELECT id FROM users WHERE name = 'user_b'").fetchone()[0]

            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

            # Attempt to update as user_b
            update_expense(expense_id, user_b_id, 200.0, "Bills", "2026-01-02", "Hack")

            row = db.execute("SELECT amount FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            assert row["amount"] == 100.0 # Should remain unchanged

class TestEditExpenseRoutes:
    def test_get_edit_unauthenticated_redirects(self, client):
        response = client.get('/expenses/1/edit')
        assert response.status_code == 302
        assert response.headers['Location'] == '/login'

    def test_get_edit_authenticated_own_expense(self, auth_client, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            user = db.execute("SELECT id FROM users WHERE name = 'testuser'").fetchone()
            user_id = user[0]
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

        response = auth_client.get(f'/expenses/{expense_id}/edit')
        assert response.status_code == 200
        assert b'Edit Expense' in response.data
        assert b'100.0' in response.data
        assert b'Food' in response.data
        assert b'2026-01-01' in response.data
        assert b'Lunch' in response.data

    def test_get_edit_authenticated_other_expense_404(self, auth_client_other, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            # Create a different user's expense
            db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("testuser", "test@test.com", "hash"))
            user_id = db.execute("SELECT id FROM users WHERE name = 'testuser'").fetchone()[0]
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

        # auth_client_other is logged in as 'otheruser'
        response = auth_client_other.get(f'/expenses/{expense_id}/edit')
        assert response.status_code == 404

    def test_get_edit_nonexistent_404(self, auth_client):
        response = auth_client.get('/expenses/999/edit')
        assert response.status_code == 404

    def test_post_edit_unauthenticated_redirects(self, client):
        response = client.post('/expenses/1/edit', data={'amount': '10.0'})
        assert response.status_code == 302
        assert response.headers['Location'] == '/login'

    def test_post_edit_valid_data_success(self, auth_client, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            user = db.execute("SELECT id FROM users WHERE name = 'testuser'").fetchone()
            user_id = user[0]
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

        data = {
            'amount': '120.00',
            'category': 'Shopping',
            'date': '2026-01-02',
            'description': 'Updated Lunch'
        }
        response = auth_client.post(f'/expenses/{expense_id}/edit', data=data, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'] == '/profile'

        with app.app_context():
            from database.db import get_db
            db = get_db()
            row = db.execute("SELECT amount, category, date, description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            assert row["amount"] == 120.0
            assert row["category"] == "Shopping"
            assert row["date"] == "2026-01-02"
            assert row["description"] == "Updated Lunch"

    def test_post_edit_other_user_expense_404(self, auth_client_other, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            # Expense owned by testuser
            db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("testuser", "test@test.com", "hash"))
            user_id = db.execute("SELECT id FROM users WHERE name = 'testuser'").fetchone()[0]
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

        data = {'amount': '200.00', 'category': 'Food', 'date': '2026-01-01', 'description': 'Hack'}
        response = auth_client_other.post(f'/expenses/{expense_id}/edit', data=data)
        assert response.status_code == 404

    @pytest.mark.parametrize("amount, category, date, description, expected_error", [
        ("", "Food", "2026-01-01", "Desc", "amount"),               # Missing amount
        ("0", "Food", "2026-01-01", "Desc", "amount"),               # Zero amount
        ("-10", "Food", "2026-01-01", "Desc", "amount"),            # Negative amount
        ("abc", "Food", "2026-01-01", "Desc", "amount"),            # Non-numeric
        ("10.00", "InvalidCat", "2026-01-01", "Desc", "category"),   # Invalid category
        ("10.00", "Food", "not-a-date", "Desc", "date"),            # Invalid date format
        ("10.00", "Food", "2026/01/01", "Desc", "date"),            # Wrong date format
    ])
    def test_post_edit_validation_fails(self, auth_client, app, amount, category, date, description, expected_error):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            user = db.execute("SELECT id FROM users WHERE name = 'testuser'").fetchone()
            user_id = user[0]
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

        data = {'amount': amount, 'category': category, 'date': date, 'description': description}
        response = auth_client.post(f'/expenses/{expense_id}/edit', data=data)

        assert response.status_code == 200
        assert expected_error.encode() in response.data.lower()
        assert b'<form' in response.data

    def test_post_edit_empty_description_success(self, auth_client, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            user = db.execute("SELECT id FROM users WHERE name = 'testuser'").fetchone()
            user_id = user[0]
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            expense_id = cursor.lastrowid
            db.commit()

        data = {
            'amount': '100.00',
            'category': 'Food',
            'date': '2026-01-01',
            'description': ''
        }
        response = auth_client.post(f'/expenses/{expense_id}/edit', data=data, follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            from database.db import get_db
            db = get_db()
            row = db.execute("SELECT description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            assert row["description"] is None

    def test_profile_page_has_edit_links(self, auth_client, app):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            user = db.execute("SELECT id FROM users WHERE name = 'testuser'").fetchone()
            user_id = user[0]
            db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()

        response = auth_client.get('/profile')
        assert response.status_code == 200
        assert b'Edit' in response.data
        assert b'/expenses/' in response.data
        assert b'/edit' in response.data
