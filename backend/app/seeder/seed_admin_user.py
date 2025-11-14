"""
Create an interactive admin user seeder.
Args:
 - email: User's email address
 - username: User's username
 - password: User's password
 - confirm_password: Confirmation of the user's password
"""
import sys
import getpass
from sqlalchemy.orm import Session
from app.models import User
from app.core.security import get_password_hash
from app.db.session import SessionLocal


def seed_admin_user(
    db: Session,
    email: str = "admin@example.com",
    username: str = "admin",
    password: str = "adminpass",
    confirm_password: str = "adminpass"
):
    # Validate passwords match
    if password != confirm_password:
        return None
    
    # Validate required fields
    if not email or not username or not password:
        return None

    user = User(
        email=email,
        username=username,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_superuser=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


if __name__ == "__main__":
    db = SessionLocal()
    try:
        # Prompt for user details
        email = input(
            "Enter admin email: "
        )
        username = input(
            "Enter admin username: "
        )
        try:
            password = getpass.getpass(
                "Enter admin password: "
            )
            confirm_password = getpass.getpass(
                "Confirm admin password: "
            )
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            sys.exit(1)

        admin_user = seed_admin_user(
            db,
            email=email,
            username=username,
            password=password,
            confirm_password=confirm_password
        )

        if admin_user is None:
            print("Error: Failed to create admin user.")
            print("Please check that:")
            print("  - Passwords match")
            print("  - All required fields are provided")
            sys.exit(1)
        print(
            f"Admin user created: {admin_user.email} / {admin_user.username}"
        )
    except Exception as e:
        print("Error creating admin user:")
        print(e)
    finally:
        db.close()
