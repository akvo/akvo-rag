from sqlalchemy.orm import Session
from app.models.prompt import PromptDefinition, PromptNameEnum, PromptVersion


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
            dynamic_content = (
                "You are given a chat history and the user's latest question. Your task is to rewrite the user's input as a clear, "
                "standalone question that fully captures their intent. The reformulated question must be understandable on its own, "
                "without requiring access to earlier parts of the conversation.\n\n"
                "Your reformulated question should:\n"
                "1. Retain the user's original language and tone.\n"
                "2. Be specific and context-aware.\n"
                "3. Be suitable for use in retrieval or question-answering over a knowledge base.\n\n"
            )

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

    def _get_citation_static_suffix(self, context_placeholder: str) -> str:
        return (
            f"\n\nContext: {context_placeholder}\n\n"
            "Remember:\n"
            "- Cite contexts by their position number (1 for first context, 2 for second, etc.).\n"
            "- Use citation format: [citation:x] at the end of each sentence where applicable.\n"
            "- If a sentence is supported by multiple contexts, use [citation:1][citation:2].\n"
            "- Do not blindly repeat the context — paraphrase instead."
        )

    def _get_strict_static_suffix(self, context_placeholder: str) -> str:
        return (
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
            dynamic_content = (
                "You are given a user question. Write a clean, concise, and accurate answer using only the provided context. "
                "Keep your answer under 1024 tokens. If the context is insufficient, say 'information is missing on [topic]'. "
                "Answer in the same language as the question. Do not copy the context verbatim — paraphrase instead."
            )

        return f"{dynamic_content.strip()}{self._get_citation_static_suffix(context_placeholder)}"

    def get_full_qa_strict_prompt(
        self, context_placeholder: str = "{context}"
    ) -> str:
        try:
            dynamic_content = self.get_active_prompt_content(
                PromptNameEnum.qa_strict_prompt
            )
        except ValueError:
            print("Warning: qa_strict_prompt not found in DB, using fallback.")
            dynamic_content = (
                "You are a highly knowledgeable and factual AI assistant. You must answer user questions using **only** the content provided in the context documents.\n\n"
                "### Strict Answering Rules:\n"
                "1. **Use Context Only**:\n"
                "   - Do not use any prior knowledge or make assumptions.\n"
                "   - Use only the documents provided in this prompt.\n"
                "   - If the answer is not present in the context, you must say so.\n"
                "2. **If Information Is Missing**:\n"
                "   - Respond with: 'Information is missing on [specific topic] based on the provided context.'\n"
                "   - If partial information exists, summarize what's known and what's missing.\n"
                "3. **Language & Style**:\n"
                "   - Be concise, clear, and formal. Paraphrase instead of copying directly.\n"
                "4. **Token Limit**:\n"
                "   - Limit answer to 1024 tokens.\n"
            )

        return f"{dynamic_content.strip()}{self._get_strict_static_suffix(context_placeholder)}"
