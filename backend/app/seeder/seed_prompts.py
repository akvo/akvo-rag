import sys
import logging

from sqlalchemy.exc import SQLAlchemyError
from app.db.session import SessionLocal
from app.models.prompt import PromptDefinition, PromptVersion, PromptNameEnum
from app.constants import (
    DEFAULT_CONTEXTUALIZE_PROMPT,
    DEFAULT_QA_STRICT_PROMPT,
    DEFAULT_QA_FLEXIBLE_PROMPT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the initial prompts and versions
INITIAL_PROMPTS = {
    PromptNameEnum.contextualize_q_system_prompt: {
        "content": DEFAULT_CONTEXTUALIZE_PROMPT,
        "version": 1,
        "is_active": True,
        "activation_reason": "Initial seed - default contextualization prompt",
    },
    PromptNameEnum.qa_flexible_prompt: {
        "content": DEFAULT_QA_FLEXIBLE_PROMPT,
        "version": 1,
        "is_active": True,
        "activation_reason": "Initial seed - flexible QA prompt",
    },
    PromptNameEnum.qa_strict_prompt: {
        "content": DEFAULT_QA_STRICT_PROMPT,
        "version": 1,
        "is_active": True,
        "activation_reason": "Initial seed - strict QA prompt",
    },
}


def seed_prompts():
    db = SessionLocal()
    try:
        for prompt_name, prompt_data in INITIAL_PROMPTS.items():
            # Check if definition already exists
            definition = (
                db.query(PromptDefinition)
                .filter_by(name=prompt_name.value)
                .first()
            )

            if not definition:
                definition = PromptDefinition(name=prompt_name.value)
                db.add(definition)
                db.flush()

                version = PromptVersion(
                    prompt_definition_id=definition.id,
                    content=prompt_data["content"],
                    version_number=prompt_data["version"],
                    is_active=prompt_data["is_active"],
                    activation_reason=prompt_data["activation_reason"],
                )
                db.add(version)
                logger.info("Seeded new prompt: %s", prompt_name)
            else:
                # Check if the latest active version matches the current content
                active_version = (
                    db.query(PromptVersion)
                    .filter_by(
                        prompt_definition_id=definition.id, is_active=True
                    )
                    .first()
                )

                if (
                    not active_version
                    or active_version.content != prompt_data["content"]
                ):
                    # Deactivate existing active versions
                    db.query(PromptVersion).filter_by(
                        prompt_definition_id=definition.id
                    ).update({"is_active": False})

                    # Get the highest version number
                    from sqlalchemy import func

                    max_version = (
                        db.query(func.max(PromptVersion.version_number))
                        .filter_by(prompt_definition_id=definition.id)
                        .scalar()
                        or 0
                    )

                    new_version = PromptVersion(
                        prompt_definition_id=definition.id,
                        content=prompt_data["content"],
                        version_number=max_version + 1,
                        is_active=True,
                        activation_reason=(
                            "Added new active version via seeder sync"
                        ),
                    )
                    db.add(new_version)
                    logger.info(
                        "Added new active version %d for: %s",
                        max_version + 1,
                        prompt_name,
                    )
                else:
                    logger.info(
                        "Prompt version is up to date: %s", prompt_name
                    )

        db.commit()
        logger.info("✅ Prompt seeding/sync completed.")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error("❌ Error during seeding:", str(e), file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    seed_prompts()
