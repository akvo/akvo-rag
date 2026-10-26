import logging
from typing import Any, Dict, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.constants import (
    DEFAULT_CONTEXTUALIZE_PROMPT,
    DEFAULT_QA_FLEXIBLE_PROMPT,
    DEFAULT_QA_STRICT_PROMPT,
)
from app.models.prompt import PromptDefinition, PromptNameEnum, PromptVersion

logger = logging.getLogger("prompt_service")

FALLBACK_MAP: Dict[PromptNameEnum, str] = {
    PromptNameEnum.contextualize_q_system_prompt: DEFAULT_CONTEXTUALIZE_PROMPT,
    PromptNameEnum.qa_strict_prompt: DEFAULT_QA_STRICT_PROMPT,
    PromptNameEnum.qa_flexible_prompt: DEFAULT_QA_FLEXIBLE_PROMPT,
}

STATIC_CONTEXT_RULE: str = (
    "---\n"
    "**Static Rule for Context-Aware Inputs:**\n"
    "If the user refers to previous conversation context or asks for "
    "a stylistic change — for example:\n"
    '- "What did we talk about?"\n'
    '- "Can you explain in easy way?"\n'
    '- "Summarize our chat"\n'
    '- "Make it shorter"\n\n'
    "Then you must:\n"
    "- Carefully review the chat history to extract the relevant "
    "subject or concept.\n"
    "- Integrate that subject into the reformulated question.\n"
    "- If the request is stylistic, preserve the subject and append "
    "the intent in parentheses.\n"
    "  Example: 'What is living income? (Instruction: explain simply)'\n"
    "- Ensure the rewritten question captures all specific references "
    "or intent implied by the user's latest message.\n"
)

CONTEXTUALIZE_CLOSING_INSTRUCTION: str = (
    "Focus on maintaining the user’s intent while making the "
    "question precise and independently interpretable."
)

QA_FLEXIBLE_SUFFIX: str = (
    "\n\nContext: {context}\n\n"
    "Remember:\n"
    "- Cite contexts by their position number (1 for first context, 2 "
    "for second, etc.).\n"
    "- Use citation format: [citation:x] at the end of each sentence "
    "where applicable.\n"
    "- If a sentence is supported by multiple contexts, use "
    "[citation:1][citation:2].\n"
    "- Do not blindly repeat the context — paraphrase instead."
)

QA_STRICT_SUFFIX: str = (
    "\n\n### Provided Context:\n{context}\n\n"
    "**Important Answering Rules:**\n"
    "- Use **ONLY** current context for retrieval queries.\n"
    "- **Exception**: Use **Chat History** only if the intent is a "
    "'memory_query' (meta-chat about the conversation).\n"
    "- **Citation (MANDATORY)**: Every sentence that uses information "
    "from the context MUST end with `[citation:x]` where x is the "
    "document position number (1 = first document, 2 = second, etc.). "
    "Multiple sources: `[citation:1][citation:2]`.\n"
    "- Do NOT use filenames or page numbers for citations.\n"
    "- If the answer is not found in the context, state so clearly "
    "and do NOT include any `[citation:x]` markers.\n"
    "- Always paraphrase—never repeat context verbatim."
)


class PromptService:
    def __init__(self, db: Optional[Union[Session, AsyncSession, Any]] = None):
        self.db = db

    def get_active_prompt_content(
        self,
        prompt_name: PromptNameEnum,
        app_custom_prompt: Optional[str] = None,
    ) -> str:
        """
        Resolves prompt with 3-tier fallback (Synchronous):
        1. App custom override (if provided)
        2. Active version in PostgreSQL 17 database
        3. Hardcoded Python constant fallback
        """
        if app_custom_prompt and app_custom_prompt.strip():
            logger.debug(
                "Using app-specific custom prompt for '%s'", prompt_name.value
            )
            return app_custom_prompt.strip()

        if self.db is not None:
            try:
                if hasattr(self.db, "query"):
                    prompt = (
                        self.db.query(PromptVersion)
                        .join(PromptDefinition)
                        .filter(PromptDefinition.name == prompt_name.value)
                        .filter(PromptVersion.is_active == True)  # noqa: E712
                        .order_by(PromptVersion.version_number.desc())
                        .first()
                    )
                    if prompt and prompt.content and prompt.content.strip():
                        return prompt.content.strip()
                elif hasattr(self.db, "execute"):
                    stmt = (
                        select(PromptVersion.content)
                        .join(
                            PromptDefinition,
                            PromptVersion.prompt_definition_id
                            == PromptDefinition.id,
                        )
                        .where(
                            PromptDefinition.name == prompt_name.value,
                            PromptVersion.is_active == True,  # noqa: E712
                        )
                        .order_by(PromptVersion.version_number.desc())
                        .limit(1)
                    )
                    res = self.db.execute(stmt)
                    content = res.scalar_one_or_none()
                    if content and content.strip():
                        return content.strip()
            except Exception as e:
                logger.warning(
                    "Failed to query active prompt '%s' from DB: %s. "
                    "Falling back to constant.",
                    prompt_name.value,
                    str(e),
                )

        logger.info(
            "Using default fallback constant for '%s'", prompt_name.value
        )
        return FALLBACK_MAP.get(
            prompt_name, DEFAULT_QA_FLEXIBLE_PROMPT
        ).strip()

    async def get_active_prompt_content_async(
        self,
        prompt_name: PromptNameEnum,
        app_custom_prompt: Optional[str] = None,
    ) -> str:
        """
        Resolves prompt with 3-tier fallback (Asynchronous):
        1. App custom override (if provided)
        2. Active version in PostgreSQL 17 database
        3. Hardcoded Python constant fallback
        """
        if app_custom_prompt and app_custom_prompt.strip():
            logger.debug(
                "Using app-specific custom prompt for '%s'", prompt_name.value
            )
            return app_custom_prompt.strip()

        if self.db is not None:
            try:
                stmt = (
                    select(PromptVersion.content)
                    .join(
                        PromptDefinition,
                        PromptVersion.prompt_definition_id
                        == PromptDefinition.id,
                    )
                    .where(
                        PromptDefinition.name == prompt_name.value,
                        PromptVersion.is_active == True,  # noqa: E712
                    )
                    .order_by(PromptVersion.version_number.desc())
                    .limit(1)
                )
                res = await self.db.execute(stmt)
                content = res.scalar_one_or_none()
                if content and content.strip():
                    return content.strip()
            except Exception as e:
                logger.warning(
                    "Failed to async query active prompt '%s' from DB: %s. "
                    "Falling back to constant.",
                    prompt_name.value,
                    str(e),
                )

        logger.info(
            "Using default fallback constant for '%s'", prompt_name.value
        )
        return FALLBACK_MAP.get(
            prompt_name, DEFAULT_QA_FLEXIBLE_PROMPT
        ).strip()

    def build_full_prompt(
        self, dynamic: str, static: str, closing: str = ""
    ) -> str:
        parts = [dynamic.strip()]
        if static and static.strip():
            parts.append(static.strip())
        if closing and closing.strip():
            parts.append(closing.strip())
        return "\n\n".join(parts)

    def get_full_contextualize_prompt(
        self, app_custom_prompt: Optional[str] = None
    ) -> str:
        dynamic_content = self.get_active_prompt_content(
            prompt_name=PromptNameEnum.contextualize_q_system_prompt,
            app_custom_prompt=app_custom_prompt,
        )
        return self.build_full_prompt(
            dynamic_content,
            STATIC_CONTEXT_RULE,
            CONTEXTUALIZE_CLOSING_INSTRUCTION,
        )

    async def get_full_contextualize_prompt_async(
        self, app_custom_prompt: Optional[str] = None
    ) -> str:
        dynamic_content = await self.get_active_prompt_content_async(
            prompt_name=PromptNameEnum.contextualize_q_system_prompt,
            app_custom_prompt=app_custom_prompt,
        )
        return self.build_full_prompt(
            dynamic_content,
            STATIC_CONTEXT_RULE,
            CONTEXTUALIZE_CLOSING_INSTRUCTION,
        )

    def get_full_qa_flexible_prompt(
        self, app_custom_prompt: Optional[str] = None
    ) -> str:
        dynamic_content = self.get_active_prompt_content(
            prompt_name=PromptNameEnum.qa_flexible_prompt,
            app_custom_prompt=app_custom_prompt,
        )
        return f"{dynamic_content.strip()}{QA_FLEXIBLE_SUFFIX}"

    async def get_full_qa_flexible_prompt_async(
        self, app_custom_prompt: Optional[str] = None
    ) -> str:
        dynamic_content = await self.get_active_prompt_content_async(
            prompt_name=PromptNameEnum.qa_flexible_prompt,
            app_custom_prompt=app_custom_prompt,
        )
        return f"{dynamic_content.strip()}{QA_FLEXIBLE_SUFFIX}"

    def get_full_qa_strict_prompt(
        self, app_custom_prompt: Optional[str] = None
    ) -> str:
        dynamic_content = self.get_active_prompt_content(
            prompt_name=PromptNameEnum.qa_strict_prompt,
            app_custom_prompt=app_custom_prompt,
        )
        return f"{dynamic_content.strip()}{QA_STRICT_SUFFIX}"

    async def get_full_qa_strict_prompt_async(
        self, app_custom_prompt: Optional[str] = None
    ) -> str:
        dynamic_content = await self.get_active_prompt_content_async(
            prompt_name=PromptNameEnum.qa_strict_prompt,
            app_custom_prompt=app_custom_prompt,
        )
        return f"{dynamic_content.strip()}{QA_STRICT_SUFFIX}"
