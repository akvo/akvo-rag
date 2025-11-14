"""
Test the admin user seeder.
Ensure that an admin user can be created with the specified details.
Path: backend/app/seeder/seed_admin_user.py
"""

from sqlalchemy.orm import Session
from app.seeder.seed_admin_user import seed_admin_user


class TestSeedAdminUser:

    def test_seed_admin_user(self, db: Session):
        email = "admin@example.com"
        username = "admin"
        password = "adminpass"
        confirm_password = "adminpass"

        admin_user = seed_admin_user(
            db,
            email=email,
            username=username,
            password=password,
            confirm_password=confirm_password
        )

        assert admin_user.email == email
        assert admin_user.username == username
        assert admin_user.is_active is True
        assert admin_user.is_superuser is True

    def test_seed_admin_user_password_mismatch(self, db: Session):
        email = "admin@example.com"
        username = "admin"
        password = "adminpass"
        confirm_password = "wrongpass"

        admin_user = seed_admin_user(
            db,
            email=email,
            username=username,
            password=password,
            confirm_password=confirm_password
        )

        assert admin_user is None

    def test_seed_admin_user_missing_details(self, db: Session):
        email = ""
        username = "admin"
        password = "adminpass"
        confirm_password = "adminpass"

        admin_user = seed_admin_user(
            db,
            email=email,
            username=username,
            password=password,
            confirm_password=confirm_password
        )

        assert admin_user is None
