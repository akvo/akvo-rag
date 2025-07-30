from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.api.api_v1.auth import get_current_user
from app.db.session import get_db
from app.models import user as user_model
from app.models.prompt import PromptDefinition, PromptVersion, PromptNameEnum
from app.schemas import prompt as schema
from app.schemas.system_setting import TopKUpdate, SystemSettingResponse
from app.services.system_settings_service import SystemSettingsService

router = APIRouter()


# Utility/service logic
def get_prompt_by_name(db: Session, name: PromptNameEnum):
    return (
        db.query(PromptDefinition)
        .options(
            joinedload(PromptDefinition.versions).joinedload(
                PromptVersion.activated_by_user
            )
        )
        .filter_by(name=name)
        .first()
    )


def list_all_prompts(db: Session):
    return (
        db.query(PromptDefinition)
        .options(
            joinedload(PromptDefinition.versions).joinedload(
                PromptVersion.activated_by_user
            )
        )
        .all()
    )


def create_or_update_prompt(
    db: Session,
    name: PromptNameEnum,
    content: str,
    user_id: int,
    reason: str = None,
):
    definition = get_prompt_by_name(db, name)

    if not definition:
        definition = PromptDefinition(name=name)
        db.add(definition)
        db.flush()

    # Deactivate current version if any
    db.query(PromptVersion).filter_by(
        prompt_definition_id=definition.id, is_active=True
    ).update({"is_active": False})

    # Get next version number safely
    current_versions = sorted(
        definition.versions or [], key=lambda v: v.version_number, reverse=True
    )
    next_version_number = (
        current_versions[0].version_number + 1 if current_versions else 1
    )

    new_version = PromptVersion(
        prompt_definition_id=definition.id,
        content=content,
        version_number=next_version_number,
        is_active=True,
        activated_by_user_id=user_id,
        activation_reason=reason,
    )
    db.add(new_version)
    db.commit()
    db.refresh(definition)
    return definition


# ROUTES
@router.post("/", response_model=schema.PromptResponse)
def create_prompt(
    prompt_in: schema.PromptCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    prompt = create_or_update_prompt(
        db,
        name=prompt_in.name,
        content=prompt_in.content,
        user_id=current_user.id,
        reason=prompt_in.activation_reason,
    )
    return {
        "name": prompt.name,
        "active_version": next(
            (v for v in prompt.versions if v.is_active), None
        ),
        "all_versions": prompt.versions,
    }


@router.put(
    "/{name}/reactivate/{version_id}", response_model=schema.PromptResponse
)
def reactivate_prompt_version(
    name: PromptNameEnum,
    version_id: int,
    data: schema.ReactivatePromptRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    prompt = get_prompt_by_name(db, name)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    version_to_activate = (
        db.query(PromptVersion).filter_by(id=version_id).first()
    )
    if (
        not version_to_activate
        or version_to_activate.prompt_definition_id != prompt.id
    ):
        raise HTTPException(
            status_code=404, detail="Version not found for this prompt"
        )

    # Deactivate current active version
    db.query(PromptVersion).filter_by(
        prompt_definition_id=prompt.id, is_active=True
    ).update({"is_active": False})

    # Activate selected version
    version_to_activate.is_active = True
    version_to_activate.activated_by_user_id = current_user.id
    version_to_activate.activation_reason = (
        data.reactivation_reason
        or version_to_activate.activation_reason
        or "Reactivated from history"
    )

    db.commit()
    db.refresh(version_to_activate)  # Refresh to get user relationship

    return {
        "name": prompt.name,
        "active_version": version_to_activate,
        "all_versions": prompt.versions,
    }


@router.put("/{name}", response_model=schema.PromptResponse)
def update_prompt(
    prompt_in: schema.PromptUpdate,
    name: PromptNameEnum,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    prompt = create_or_update_prompt(
        db,
        name=name,
        content=prompt_in.content,
        user_id=current_user.id,
        reason=prompt_in.activation_reason,
    )
    return {
        "name": prompt.name,
        "active_version": next(
            (v for v in prompt.versions if v.is_active), None
        ),
        "all_versions": prompt.versions,
    }


@router.get("", response_model=List[schema.PromptResponse])
def list_prompts(db: Session = Depends(get_db)):
    definitions = list_all_prompts(db)
    return [
        {
            "name": defn.name,
            "active_version": next(
                (v for v in defn.versions if v.is_active), None
            ),
            "all_versions": [],
        }
        for defn in definitions
    ]


@router.get("/{name}", response_model=schema.PromptResponse)
def get_prompt(name: PromptNameEnum, db: Session = Depends(get_db)):
    definition = get_prompt_by_name(db, name)
    if not definition:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {
        "name": definition.name,
        "active_version": next(
            (v for v in definition.versions if v.is_active), None
        ),
        "all_versions": definition.versions,
    }


@router.get("/settings/top_k", response_model=SystemSettingResponse)
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


@router.put("/settings/top_k", response_model=SystemSettingResponse)
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
