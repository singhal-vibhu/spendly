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
    })
    with flask_app.app_context():
        init_db()
        yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def user_a(client, app):
    """Creates User A and returns their ID."""
    with app.app_context():
        from database.db import create_user
        return create_user("User A", "a@test.com", "passA")

@pytest.fixture
def user_b(client, app):
    """Creates User B and returns their ID."""
    with app.app_context():
        from database.db import create_user
        return create_user("User B", "b@test.com", "passB")

@pytest.fixture
def auth_client_a(client, user_a):
    """A test client logged in as User A."""
    client.post('/login', data={'email': 'a@test.com', 'password': 'passA'})
    return client

@pytest.fixture
def auth_client_b(client, user_b):
    """A test client logged in as User B."""
    client.post('/login', data={'email': 'b@test.com', 'password': 'passB'})
    return client

class TestEditExpenseDB:
    def test_get_expense_by_id_valid(self, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

            expense = get_expense_by_id(expense_id, user_a)
            assert expense is not None
            assert expense["id"] == expense_id
            assert expense["amount"] == 100.0

    def test_get_expense_by_id_wrong_user(self, app, user_a, user_b):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

            expense = get_expense_by_id(expense_id, user_b)
            assert expense is None

    def test_get_expense_by_id_nonexistent(self, app, user_a):
        with app.app_context():
            expense = get_expense_by_id(999, user_a)
            assert expense is None

    def test_update_expense_valid(self, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

            update_expense(expense_id, user_a, 150.0, "Shopping", "2026-01-02", "New Shirt")

            with app.app_context():
                db = get_db()
                row = db.execute("SELECT amount, category, date, description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
                db.close()
                assert row["amount"] == 150.0
                assert row["category"] == "Shopping"
                assert row["date"] == "2026-01-02"
                assert row["description"] == "New Shirt"

    def test_update_expense_wrong_user(self, app, user_a, user_b):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

            update_expense(expense_id, user_b, 200.0, "Bills", "2026-01-02", "Wrong User")

            with app.app_context():
                db = get_db()
                row = db.execute("SELECT amount FROM expenses WHERE id = ?", (expense_id,)).fetchone()
                db.close()
                assert row["amount"] == 100.0 # Should not have changed

class TestEditExpenseRoutes:
    def test_get_edit_unauthenticated_redirects(self, client):
        response = client.get('/expenses/1/edit')
        assert response.status_code == 302
        assert response.headers['Location'] == '/login'

    def test_get_edit_authenticated_own_expense(self, auth_client_a, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

        response = auth_client_a.get(f'/expenses/{expense_id}/edit')
        assert response.status_code == 200
        assert b'Edit Expense' in response.data
        assert b'100.0' in response.data
        assert b'Food' in response.data

    def test_get_edit_authenticated_other_expense_404(self, auth_client_b, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

        response = auth_client_b.get(f'/expenses/{expense_id}/edit')
        assert response.status_code == 404

    def test_get_edit_nonexistent_404(self, auth_client_a):
        response = auth_client_a.get('/expenses/999/edit')
        assert response.status_code == 404

    def test_post_edit_valid_data_success(self, auth_client_a, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

        data = {
            'amount': '120.00',
            'category': 'Shopping',
            'date': '2026-01-02',
            'description': 'Updated Lunch'
        }
        response = auth_client_a.post(f'/expenses/{expense_id}/edit', data=data, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers['Location'] == '/profile'

        with app.app_context():
            from database.db import get_db
            db = get_db()
            row = db.execute("SELECT amount, category, date, description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
            db.close()
            assert row["amount"] == 120.0
            assert row["category"] == "Shopping"
            assert row["date"] == "2026-01-02"
            assert row["description"] == "Updated Lunch"

    def test_post_edit_invalid_amount_fails(self, auth_client_a, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

        data = {
            'amount': '-10.00',
            'category': 'Food',
            'date': '2026-01-01',
            'description': 'Invalid'
        }
        response = auth_client_a.post(f'/expenses/{expense_id}/edit', data=data)
        assert response.status_code == 200
        assert b'finite number greater than 0' in response.data.lower()

    def test_post_edit_invalid_category_fails(self, auth_client_a, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

        data = {
            'amount': '100.00',
            'category': 'WrongCat',
            'date': '2026-01-01',
            'description': 'Invalid'
        }
        response = auth_client_a.post(f'/expenses/{expense_id}/edit', data=data)
        assert response.status_code == 200
        assert b'valid category' in response.data.lower()

    def test_post_edit_future_date_fails(self, auth_client_a, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

        data = {
            'amount': '100.00',
            'category': 'Food',
            'date': '2099-12-31',
            'description': 'Future'
        }
        response = auth_client_a.post(f'/expenses/{expense_id}/edit', data=data)
        assert response.status_code == 200
        assert b'cannot be in the future' in response.data.lower()

    def test_post_edit_empty_description_success(self, auth_client_a, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

        data = {
            'amount': '100.00',
            'category': 'Food',
            'date': '2026-01-01',
            'description': ''
        }
        response = auth_client_a.post(f'/expenses/{expense_id}/edit', data=data, follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            from database.db import get_db
            db = get_db()
            row = db.execute("SELECT description FROM expenses WHERE id = ?", (expense_idS,)).fetchone()
            db.close()
            assert row["description"] is None

    def test_post_edit_other_user_expense_404(self, auth_client_b, app, user_a):
        with app.app_context():
            from database.db import get_db
            db = get_db()
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_a, 100.0, "Food", "2026-01-01", "Lunch")
            )
            db.commit()
            expense_id = cursor.lastrowid
            db.close()

        data = {
            'amount': '200.00',
            'category': 'Food',
            'date': '2026-01-01',
            'description': 'Hacking'
        }
        response = auth_client_b.post(f'/expenses/{expense_id}/edit', data=data)
        assert response.status_code == 404
