from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.schemas import prompt as schema
from app.models.prompt import PromptDefinition, PromptVersion, PromptNameEnum
from app.api.api_v1.auth import get_current_user
from app.db.session import get_db

router = APIRouter()


# Utility/service logic
def get_prompt_by_name(db: Session, name: PromptNameEnum):
    return db.query(PromptDefinition).filter_by(name=name).first()


def list_all_prompts(db: Session):
    return db.query(PromptDefinition).all()


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

    new_version = PromptVersion(
        prompt_definition_id=definition.id,
        content=content,
        version_number=(
            (definition.versions[0].version_number + 1)
            if definition.versions
            else 1
        ),
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


@router.get("/", response_model=List[schema.PromptResponse])
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
