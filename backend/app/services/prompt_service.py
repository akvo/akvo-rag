from sqlalchemy.orm import Session
from app.models.prompt import PromptDefinition, PromptNameEnum, PromptVersion
from app.constants import (
    DEFAULT_CONTEXTUALIZE_PROMPT,
    DEFAULT_QA_STRICT_PROMPT,
    DEFAULT_QA_FLEXIBLE_PROMPT,
)


class PromptService:
    def __init__(self, db: Session):
        self.db = db

    def get_active_prompt_content(self, prompt_name: PromptNameEnum) -> str:
        # Stub: implement actual DB access logic if needed
        raise ValueError(f"Prompt not found for {prompt_name}")

    def build_full_prompt(
        self, dynamic: str, static: str, closing: str = ""
    ) -> str:
        return f"{dynamic.strip()}\n{static.strip()}\n{closing.strip()}"

    def get_full_contextualize_prompt(self) -> str:
        try:
            dynamic_content = self.get_active_prompt_content(
                PromptNameEnum.contextualize_q_system_prompt
            )
        except ValueError:
            print(
                "Warning: contextualize_q_system_prompt not found in DB, using fallback."
            )
            dynamic_content = DEFAULT_CONTEXTUALIZE_PROMPT

        static_context_rule = (
            "---\n"
            "**Static Rule for Context-Aware Inputs:**\n"
            "If the user refers to previous conversation context — for example, phrases like:\n"
            '- "What did we talk about?"\n'
            '- "Can you remind me what I said?"\n'
            '- "Summarize our chat"\n'
            '- "What was your last response?"\n\n'
            "Then you must:\n"
            "- Carefully review the chat history to extract the relevant information.\n"
            "- Integrate that information into the reformulated question.\n"
            "- Ensure the rewritten question captures all specific references or intent implied by the user's original message.\n"
        )

        closing_instruction = "Focus on maintaining the user’s intent while making the question precise and independently interpretable."

        return self.build_full_prompt(
            dynamic_content, static_context_rule, closing_instruction
        )

    def get_full_qa_flexible_prompt(
        self, context_placeholder: str = "{context}"
    ) -> str:
        try:
            dynamic_content = self.get_active_prompt_content(
                PromptNameEnum.qa_flexible_prompt
            )
        except ValueError:
            print(
                "Warning: qa_flexible_prompt not found in DB, using fallback."
            )
            dynamic_content = DEFAULT_QA_FLEXIBLE_PROMPT

        suffix = (
            f"\n\nContext: {context_placeholder}\n\n"
            "Remember:\n"
            "- Cite contexts by their position number (1 for first context, 2 for second, etc.).\n"
            "- Use citation format: [citation:x] at the end of each sentence where applicable.\n"
            "- If a sentence is supported by multiple contexts, use [citation:1][citation:2].\n"
            "- Do not blindly repeat the context — paraphrase instead."
        )
        return f"{dynamic_content.strip()}{suffix}"

    def get_full_qa_strict_prompt(
        self, context_placeholder: str = "{context}"
    ) -> str:
        try:
            dynamic_content = self.get_active_prompt_content(
                PromptNameEnum.qa_strict_prompt
            )
        except ValueError:
            print("Warning: qa_strict_prompt not found in DB, using fallback.")
            dynamic_content = DEFAULT_QA_STRICT_PROMPT

        suffix = (
            f"\n\n### Provided Context:\n{context_placeholder}\n\n"
            "**Important Reminder:**\n"
            "- Do NOT use external knowledge, assumptions, or previous chat history.\n"
            "- Cite **only** from the current context documents.\n"
            "- Citation format: `[citation:x]`, where `x` is the context number (1, 2, 3, etc.).\n"
            "- Cite contexts by their **position number** (1 for first context, 2 for second, etc.).\n"
            "- Multiple citations should appear like `[citation:1][citation:2]`.\n"
            "- Do NOT use `[1]`, `(2)`, page numbers, or filenames.\n"
            "- Always paraphrase—never repeat the context verbatim."
        )

        return f"{dynamic_content.strip()}{suffix}"
