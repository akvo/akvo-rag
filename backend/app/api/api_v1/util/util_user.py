from sqlalchemy.orm import Session
from app.models.user import User

from sqlalchemy import and_


def get_super_user_ids(db: Session):
    super_users = (
        db.query(User.id)
        .filter(and_(
            User.is_superuser.is_(True),
            User.is_active.is_(True)
        ))
        .all()
    )
    return [u[0] for u in super_users]
