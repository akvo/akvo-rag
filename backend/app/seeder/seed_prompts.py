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
                logger.info("Seeded prompt: %s", prompt_name)
            else:
                logger.warning("Prompt already exists: %s", prompt_name)

        db.commit()
        logger.info("✅ Prompt seeding completed.")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error("❌ Error during seeding:", str(e), file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    seed_prompts()
