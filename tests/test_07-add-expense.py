import pytest
from app import app as flask_app
from database.db import init_db

@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': ':memory:',  # isolated in-memory DB per test
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
    """A test client that is already logged in."""
    client.post('/register', data={'username': 'testuser', 'password': 'testpass'})
    client.post('/login', data={'username': 'testuser', 'password': 'testpass'})
    return client

class TestAddExpense:

    # --- Access Control ---

    def test_get_add_expense_unauthenticated_redirects(self, client):
        response = client.get('/expenses/add')
        assert response.status_code == 302
        assert response.headers['Location'] == '/login'

    def test_post_add_expense_unauthenticated_redirects(self, client):
        response = client.post('/expenses/add', data={'amount': '10.00', 'category': 'Food', 'date': '2026-01-01'})
        assert response.status_code == 302
        assert response.headers['Location'] == '/login'

    # --- Form Rendering ---

    def test_get_add_expense_authenticated_renders_form(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert response.status_code == 200
        assert b'<form' in response.data
        assert b'method="POST"' in response.data

        categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
        for cat in categories:
            assert cat.encode() in response.data

    # --- Submission Happy Paths ---

    def test_post_add_expense_valid_data_success(self, auth_client, app):
        # Valid data submission
        data = {
            'amount': '50.00',
            'category': 'Food',
            'date': '2026-03-20',
            'description': 'Lunch with team'
        }
        response = auth_client.post('/expenses/add', data=data, follow_redirects=False)

        # Should redirect to profile
        assert response.status_code == 302
        assert response.headers['Location'] == '/profile'

        # Verify DB side effect
        with app.app_context():
            from database.db import get_db
            db = get_db()
            expense = db.execute(
                "SELECT amount, category, date, description FROM expenses WHERE amount = ? AND category = ?",
                (50.0, 'Food')
            ).fetchone()
            assert expense is not None
            assert expense[0] == 50.0
            assert expense[1] == 'Food'
            assert expense[2] == '2026-03-20'
            assert expense[3] == 'Lunch with team'

    def test_post_add_expense_no_description_success(self, auth_client, app):
        # Valid data, missing optional description
        data = {
            'amount': '20.00',
            'category': 'Transport',
            'date': '2026-03-21',
            'description': ''
        }
        response = auth_client.post('/expenses/add', data=data, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'] == '/profile'

        # Verify DB side effect: description should be NULL (None in Python)
        with app.app_context():
            from database.db import get_db
            db = get_db()
            expense = db.execute(
                "SELECT description FROM expenses WHERE amount = ?",
                (20.0,)
            ).fetchone()
            assert expense is not None
            assert expense[0] is None

    # --- Validation Errors ---

    @pytest.mark.parametrize("amount, category, date, description", [
        ("", "Food", "2026-03-20", "Missing amount"),            # Missing amount
        ("0", "Food", "2026-03-20", "Zero amount"),              # Zero amount
        ("-10", "Food", "2026-03-20", "Negative amount"),       # Negative amount
        ("abc", "Food", "2026-03-20", "Non-numeric amount"),    # Non-numeric
    ])
    def test_post_add_expense_invalid_amount_fails(self, auth_client, amount, category, date, description):
        data = {'amount': amount, 'category': category, 'date': date, 'description': description}
        response = auth_client.post('/expenses/add', data=data)

        assert response.status_code == 200
        assert b'error' in response.data.lower() or b'invalid' in response.data.lower()
        assert b'<form' in response.data # Form should be re-rendered

    def test_post_add_expense_invalid_category_fails(self, auth_client):
        data = {
            'amount': '10.00',
            'category': 'InvalidCategory',
            'date': '2026-03-20',
            'description': 'Testing'
        }
        response = auth_client.post('/expenses/add', data=data)

        assert response.status_code == 200
        assert b'category' in response.data.lower()
        assert b'error' in response.data.lower() or b'invalid' in response.data.lower()

    def test_post_add_expense_empty_category_fails(self, auth_client):
        data = {
            'amount': '10.00',
            'category': '',
            'date': '2026-03-20',
            'description': 'Testing'
        }
        response = auth_client.post('/expenses/add', data=data)

        assert response.status_code == 200
        assert b'category' in response.data.lower()

    @pytest.mark.parametrize("date_str", [
        ("not-a-date", "Missing/Invalid date"),
        ("", "Empty date"),
        ("2026/03/20", "Wrong format"),
    ])
    def test_post_add_expense_invalid_date_fails(self, auth_client, date_str, label):
        data = {
            'amount': '10.00',
            'category': 'Food',
            'date': date_str,
            'description': label
        }
        response = auth_client.post('/expenses/add', data=data)

        assert response.status_code == 200
        assert b'date' in response.data.lower()
        assert b'error' in response.data.lower() or b'invalid' in response.data.lower()

    # --- UI Links ---

    def test_profile_page_has_add_expense_link(self, auth_client):
        response = auth_client.get('/profile')
        assert response.status_code == 200
        # Check for a link or button that goes to /expenses/add
        assert b'/expenses/add' in response.data

    def test_navbar_has_add_expense_link_when_logged_in(self, auth_client):
        response = auth_client.get('/profile')
        assert b'Add Expense' in response.data
        assert b'/expenses/add' in response.data
