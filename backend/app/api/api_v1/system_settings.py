from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.api_v1.auth import get_current_user
from app.db.session import get_db
from app.schemas.system_setting import TopKUpdate, SystemSettingResponse
from app.services.system_settings_service import SystemSettingsService

router = APIRouter()

@router.get("/top_k", response_model=SystemSettingResponse)
def get_top_k_setting(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve the global top_k setting."""
    service = SystemSettingsService(db)
    try:
        return service.get_setting("top_k")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/top_k", response_model=SystemSettingResponse)
def update_top_k_setting(
    update_data: TopKUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update the global top_k setting."""
    service = SystemSettingsService(db)
    try:
        return service.update_top_k(update_data.top_k)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
