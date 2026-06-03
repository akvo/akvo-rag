from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from requests.exceptions import RequestException

from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(security.oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# Support set user as super user
@router.post("/register", response_model=UserResponse)
def register(*, db: Session = Depends(get_db), user_in: UserCreate) -> Any:
    """
    Register a new user.
    """
    try:
        # Check if user with this email exists
        user = db.query(User).filter(User.email == user_in.email).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="A user with this email already exists.",
            )

        # Check if user with this username exists
        user = db.query(User).filter(User.username == user_in.username).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="A user with this username already exists.",
            )

        # Create new user
        user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=security.get_password_hash(user_in.password),
            is_superuser=user_in.is_superuser,
            is_active=False,  # New users are inactive by default
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except RequestException as e:
        msg = "Network error or server is unreachable. Please try again later."
        raise HTTPException(
            status_code=503,
            detail=msg,
        ) from e


@router.post("/token", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Your account is currently inactive and "
                "requires administrator approval. "
                "Please contact your administrator to activate your account."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/test-token", response_model=UserResponse)
def test_token(current_user: User = Depends(get_current_user)) -> Any:
    """
    Test access token by getting current user.
    """
    return current_user


@router.get("/me", response_model=UserResponse)
def user_me(current_user: User = Depends(get_current_user)) -> Any:
    """
    Get user profile.
    """
    return current_user


@router.put("/user", response_model=UserResponse)
def update_user_by_email(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_in: UserUpdate,
) -> Any:
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="A user with this email not found.",
        )
    # DO NOT UPDATE USERNAME IF USER EXIST
    # user.email = user_in.email
    # user.username = user.username or user_in.username
    user.is_active = user_in.is_active
    user.is_superuser = user_in.is_superuser
    db.commit()
    db.refresh(user)
    return user


from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    PasswordResetResponse
)
from app.services.email_service import EmailService


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    *,
    db: Session = Depends(get_db),
    request_data: ForgotPasswordRequest
) -> Any:
    """
    Request password reset. Sends email with reset link.
    Always returns success to prevent email enumeration.
    """
    # Look up user by email
    user = db.query(User).filter(User.email == request_data.email).first()

    if user and user.is_active:
        # Generate reset token
        token = EmailService.generate_reset_token(db, user)

        # Send email (async)
        await EmailService.send_password_reset_email(
            email=user.email,
            reset_token=token,
            user_name=user.username
        )

    # Always return success to prevent email enumeration
    return PasswordResetResponse(
        message="If an account exists with that email, you will receive password reset instructions."
    )


@router.post("/reset-password", response_model=PasswordResetResponse)
def reset_password(
    *,
    db: Session = Depends(get_db),
    request_data: ResetPasswordRequest
) -> Any:
    """
    Reset password using valid token.
    """
    # Verify token
    user = EmailService.verify_reset_token(db, request_data.token)

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )

    # Update password
    user.hashed_password = security.get_password_hash(request_data.new_password)

    # Mark token as used
    EmailService.mark_token_as_used(db, request_data.token)

    db.commit()

    return PasswordResetResponse(
        message="Password has been reset successfully. You can now login with your new password."
    )


@router.get("/verify-reset-token/{token}")
def verify_reset_token(
    token: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Verify if a reset token is valid (for frontend validation)
    """
    user = EmailService.verify_reset_token(db, token)

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )

    return {"valid": True, "email": user.email}
