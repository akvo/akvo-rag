"""
Test user management API endpoints.
Includes tests for:
- Listing users with pagination and active status filtering.
- Toggling a user's active status.
- Admin access control.
- Error handling for non-existent users.
- Validation of response schemas.
Uses FastAPI's TestClient and pytest for testing.
"""

import pytest
from app.models import User
from app.core.security import get_password_hash


@pytest.fixture
def admin_token(db, client):
    """Fixture for an admin user."""
    user = User(
        id=1,
        username="admin",
        email="admin@example.com",
        is_active=True,
        is_superuser=True,
    )
    user.hashed_password = get_password_hash("adminpass")
    db.add(user)
    db.commit()
    db.refresh(user)

    res = client.post(
        "/api/auth/token",
        data={"username": "admin", "password": "adminpass"},
    )
    token = res.json().get("access_token")
    return token


@pytest.fixture
def user_token(db, client):
    """Fixture for a regular user."""
    user = User(
        id=2,
        username="user",
        email="user@example.com",
        is_active=True,
        is_superuser=False
    )
    user.hashed_password = get_password_hash("userpass")
    db.add(user)
    db.commit()
    db.refresh(user)

    res = client.post(
        "/api/auth/token",
        data={"username": "user", "password": "userpass"},
    )
    token = res.json().get("access_token")
    return token


class TestUsersEndpoints:
    """Test suite for User management API endpoints."""

    def test_read_users_admin_access(self, db, client, admin_token):
        """Test reading users with admin access."""
        # Create test users
        user1 = User(
            id=3,
            username="user1",
            email="user1@example.com",
            is_active=True,
            is_superuser=False,
            hashed_password=get_password_hash("pass1")
        )
        user2 = User(
            id=4,
            username="user2",
            email="user2@example.com",
            is_active=True,
            is_superuser=False,
            hashed_password=get_password_hash("pass2")
        )
        db.add(user1)
        db.add(user2)
        db.commit()

        response = client.get(
            "/api/users/",
            headers={
                "Authorization": f"Bearer {admin_token}"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert data["page"] == 1
        assert data["size"] == 10
        emails = [u["email"] for u in data["data"]]
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails

    def test_toggle_user_active_status(self, db, client, admin_token):
        """Test toggling a user's active status."""
        # Create test user
        user = User(
            id=5,
            username="user_to_toggle",
            email="toggle@example.com",
            is_active=True,
            is_superuser=False,
            hashed_password=get_password_hash("pass")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.patch(
            f"/api/users/{user.id}/toggle-active",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_read_users_non_admin_access(self, db, client, user_token):
        """Test reading users with non-admin access."""
        response = client.get(
            "/api/users/",
            headers={
                "Authorization": f"Bearer {user_token}"
            }
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "Not authorized to access this resource"
        )

    def test_toggle_user_active_status_non_existent_user(
        self, db, client, admin_token
    ):
        """Test toggling active status for a non-existent user."""
        response = client.patch(
            "/api/users/999999/toggle-active",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_read_users_with_active_filter(self, db, client, admin_token):
        """Test reading users with is_active filter."""
        # Create test users
        active_user = User(
            id=6,
            username="active_user",
            email="active@example.com",
            is_active=True,
            is_superuser=False,
            hashed_password=get_password_hash("pass")
        )
        inactive_user = User(
            id=7,
            username="inactive_user",
            email="inactive@example.com",
            is_active=False,
            is_superuser=False,
            hashed_password=get_password_hash("pass")
        )
        db.add(active_user)
        db.add(inactive_user)
        db.commit()

        response = client.get(
            "/api/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"is_active": True},
        )

        assert response.status_code == 200
        data = response.json()
        # Check all returned users are active
        for user in data["data"]:
            assert user["is_active"] is True

    def test_read_users_with_search_filter(self, db, client, admin_token):
        """Test reading users with search filter."""
        # Create test users
        search_user = User(
            id=9,
            username="search_user",
            email="search@example.com",
            is_active=True,
            is_superuser=False,
            hashed_password=get_password_hash("pass")
        )
        db.add(search_user)
        db.commit()

        response = client.get(
            "/api/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"search": "search_user"},
        )

        assert response.status_code == 200
        data = response.json()
        # Check all returned users match the search criteria
        for user in data["data"]:
            assert "search_user" in user["username"]
            assert "search@example.com" in user["email"]

    def test_read_users_pagination(self, db, client, admin_token):
        """Test reading users with pagination parameters."""
        # Create test users (12 users + 1 admin = 13 total)
        for i in range(12):
            user = User(
                id=10 + i,
                username=f"paginated_user_{i}",
                email=f"paginated{i}@example.com",
                is_active=True,
                is_superuser=False,
                hashed_password=get_password_hash("pass")
            )
            db.add(user)
        db.commit()

        # Request page 2 with size 10
        # Page 2 should skip first 10 items and return remaining 3
        response = client.get(
            "/api/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"page": 2, "size": 10},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 13
        assert response.json()["page"] == 2
        assert response.json()["size"] == 10
        assert len(response.json()["data"]) == 3

    def test_toggle_user_active_status_response_schema(
        self, db, client, admin_token
    ):
        """Test response schema for toggling user active status."""
        user = User(
            id=8,
            username="schema_user",
            email="schema@example.com",
            is_active=True,
            is_superuser=False,
            hashed_password=get_password_hash("pass")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.patch(
            f"/api/users/{user.id}/toggle-active",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "is_active" in data
        assert "is_superuser" in data
        assert data["id"] == user.id
        assert data["email"] == "schema@example.com"
        assert data["is_active"] is False
        assert data["is_superuser"] is False
