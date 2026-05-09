import pytest
from datetime import datetime, timedelta
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
    client.post('/register', data={'name': 'Test User', 'email': 'test@example.com', 'password': 'password123', 'confirm_password': 'password123'})
    client.post('/login', data={'email': 'test@example.com', 'password': 'password123'})
    return client

def insert_expense(client, amount, category, date, description="Test expense"):
    """Helper to insert expenses for a specific user."""
    from database.db import get_db
    with flask_app.app_context():
        db = get_db()
        # Assuming user_id 1 is our test user
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (1, amount, category, date, description)
        )
        db.commit()

class TestProfileDateFilters:

    def test_profile_auth_guard(self, client):
        """Verify that /profile redirects to /login if not authenticated."""
        response = client.get('/profile')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_profile_unfiltered_view(self, auth_client):
        """Verify /profile without params shows all expenses and sets active_preset to all_time."""
        insert_expense(auth_client, 100.0, "Food", "2026-01-01")
        insert_expense(auth_client, 200.0, "Transport", "2026-05-01")

        response = auth_client.get('/profile')
        assert response.status_code == 200
        assert b"300.00" in response.data
        assert b"All Time" in response.data

    @pytest.mark.parametrize("preset, expected_count", [
        ("this_month", 1),
        ("last_3_months", 2),
        ("last_6_months", 3),
        ("all_time", 3),
    ])
    def test_profile_presets(self, auth_client, preset, expected_count):
        """Verify that presets filter the data correctly based on relative time."""
        today = datetime.now()

        # Expense 1: Today (matches all)
        insert_expense(auth_client, 10.0, "Food", today.strftime("%Y-%m-%d"))
        # Expense 2: 1 month ago (matches 3, 6, all)
        one_month_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        insert_expense(auth_client, 20.0, "Food", one_month_ago)
        # Expense 3: 5 months ago (matches 6, all)
        five_months_ago = (today - timedelta(days=150)).strftime("%Y-%m-%d")
        insert_expense(auth_client, 30.0, "Food", five_months_ago)

        response = auth_client.get(f'/profile?preset={preset}')
        assert response.status_code == 200

        if preset == "this_month":
            assert b"10.00" in response.data
            assert b"50.00" not in response.data # 20 + 30
        elif preset == "last_3_months":
            assert b"30.00" in response.data # 10 + 20
            assert b"60.00" not in response.data # 10 + 20 + 30
        elif preset == "last_6_months" or preset == "all_time":
            assert b"60.00" in response.data

    def test_custom_date_range_valid(self, auth_client):
        """Verify that valid date_from and date_to filter data strictly."""
        insert_expense(auth_client, 111.0, "Food", "2026-01-01")
        insert_expense(auth_client, 222.0, "Food", "2026-01-15")
        insert_expense(auth_client, 333.0, "Food", "2026-02-01")

        response = auth_client.get('/profile?date_from=2026-01-01&date_to=2026-01-31')
        assert response.status_code == 200
        assert b"333.00" in response.data # 111 + 222

    def test_date_range_inverted(self, auth_client):
        """Verify that date_from > date_to flashes error and falls back to unfiltered."""
        insert_expense(auth_client, 100.0, "Food", "2026-01-01")

        response = auth_client.get('/profile?date_from=2026-02-01&date_to=2026-01-01')
        assert response.status_code == 200
        assert b"Start date must be before end date." in response.data
        assert b"100.00" in response.data

    def test_malformed_date_fallback(self, auth_client):
        """Verify that malformed dates silently fall back to unfiltered view."""
        insert_expense(auth_client, 100.0, "Food", "2026-01-01")

        response = auth_client.get('/profile?date_from=not-a-date&date_to=2026-01-01')
        assert response.status_code == 200
        assert b"100.00" in response.data

    def test_partial_date_fallback(self, auth_client):
        """Verify that providing only one date parameter falls back to unfiltered."""
        insert_expense(auth_client, 100.0, "Food", "2026-01-01")

        response = auth_client.get('/profile?date_from=2026-01-01')
        assert response.status_code == 200
        assert b"100.00" in response.data

    def test_empty_state_range(self, auth_client):
        """Verify that a range with no expenses shows zeros and empty categories."""
        insert_expense(auth_client, 100.0, "Food", "2026-01-01")

        response = auth_client.get('/profile?date_from=2026-05-01&date_to=2026-05-10')
        assert response.status_code == 200
        assert b"0.00" in response.data
        assert b"0" in response.data

    def test_active_preset_highlighting(self, auth_client):
        """Verify that the active_preset is reflected in the response."""
        response = auth_client.get('/profile?preset=this_month')
        assert response.status_code == 200
        assert b"active" in response.data
