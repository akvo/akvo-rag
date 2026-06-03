import logging

from sqlalchemy.orm import Session
from app.models.prompt import PromptDefinition, PromptNameEnum, PromptVersion
from app.constants import (
    DEFAULT_CONTEXTUALIZE_PROMPT,
    DEFAULT_QA_STRICT_PROMPT,
    DEFAULT_QA_FLEXIBLE_PROMPT,
)

logger = logging.getLogger(__name__)


class PromptService:
    def __init__(self, db: Session):
        self.db = db

    def get_active_prompt_content(self, prompt_name: PromptNameEnum) -> str:
        prompt = (
            self.db.query(PromptVersion)
            .join(PromptDefinition)
            .filter(PromptDefinition.name == prompt_name.value)
            .filter(PromptVersion.is_active == 1)
            .order_by(PromptVersion.version_number.desc())
            .first()
        )

        if not prompt:
            raise ValueError(
                f"Prompt not found or not active for: {prompt_name}"
            )

        return prompt.content

    def build_full_prompt(
        self, dynamic: str, static: str, closing: str = ""
    ) -> str:
        return f"{dynamic.strip()}\n{static.strip()}\n{closing.strip()}"

    def get_full_contextualize_prompt(self) -> str:
        try:
            dynamic_content = self.get_active_prompt_content(
                prompt_name=PromptNameEnum.contextualize_q_system_prompt
            )
        except ValueError:
            logger.warning(
                "contextualize_q_system_prompt not found in DB, using fallback."
            )
            dynamic_content = DEFAULT_CONTEXTUALIZE_PROMPT

        static_context_rule = (
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
            "  Example: 'What is living income? (Instruction: explain "
            "simply)'\n"
            "- Ensure the rewritten question captures all specific references "
            "or intent implied by the user's latest message.\n"
        )

        closing_instruction = (
            "Focus on maintaining the user’s intent while making the "
            "question precise and independently interpretable."
        )

        return self.build_full_prompt(
            dynamic_content, static_context_rule, closing_instruction
        )

    def get_full_qa_flexible_prompt(self) -> str:
        # {context} is fixed: LangChain resolves it at inference time.
        try:
            dynamic_content = self.get_active_prompt_content(
                prompt_name=PromptNameEnum.qa_flexible_prompt
            )
        except ValueError:
            logger.warning(
                "qa_flexible_prompt not found in DB, using fallback."
            )
            dynamic_content = DEFAULT_QA_FLEXIBLE_PROMPT

        suffix = (
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
        return f"{dynamic_content.strip()}{suffix}"

    def get_full_qa_strict_prompt(self) -> str:
        # {context} is fixed: LangChain resolves it at inference time.
        try:
            dynamic_content = self.get_active_prompt_content(
                prompt_name=PromptNameEnum.qa_strict_prompt
            )
        except ValueError:
            logger.warning(
                "qa_strict_prompt not found in DB, using fallback."
            )
            dynamic_content = DEFAULT_QA_STRICT_PROMPT

        suffix = (
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

        return f"{dynamic_content.strip()}{suffix}"
