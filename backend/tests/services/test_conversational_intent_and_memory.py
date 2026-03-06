import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from app.services.query_answering_workflow import (
    classify_intent_node,
    contextualize_node,
    GraphState,
)


@pytest.mark.unit
class TestConversationalIntentAndMemory:
    """Tests for conversational memory intent and stylistic query alignment."""

    @pytest.mark.asyncio
    async def test_classify_intent_memory_query_detection(self, monkeypatch):
        """
        Verify that 'memory_query' intent is correctly identified for
        recall questions.
        """

        async def fake_ainvoke(msgs):
            return SimpleNamespace(content='{"intent": "memory_query"}')

        fake_llm = MagicMock()
        fake_llm.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: fake_llm,
        )

        state = {"query": "What did we just talk about?"}
        new_state = await classify_intent_node(state)
        assert new_state["intent"] == "memory_query"

    @pytest.mark.asyncio
    async def test_contextualize_preserves_stylistic_instructions(
        self, monkeypatch
    ):
        """Verify that stylistic instructions are preserved."""

        async def fake_ainvoke(inputs):
            # Simulate LLM following the new rule: subject + instruction
            return SimpleNamespace(
                content="What is living income? (Instruction: explain simply)"
            )

        fake_chain = MagicMock()
        fake_chain.ainvoke = fake_ainvoke

        monkeypatch.setattr(
            "app.services.query_answering_workflow"
            ".ChatPromptTemplate.from_messages",
            lambda msgs: MagicMock(__or__=lambda self, other: fake_chain),
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: MagicMock(),
        )

        state: GraphState = {
            "query": "explain in easy way",
            "chat_history": [
                {"role": "user", "content": "What is living income?"}
            ],
            "contextualize_prompt_str": "prompt",
            "intent": "knowledge_query",
        }

        new_state = await contextualize_node(state)
        assert "living income" in new_state["contextual_query"]
        assert "Instruction: explain simply" in new_state["contextual_query"]

    @pytest.mark.asyncio
    async def test_memory_query_configures_permissive_qa_prompt(
        self, monkeypatch
    ):
        """Verify that memory_query intent sets the permissive prompt."""

        async def fake_ainvoke(inputs):
            return SimpleNamespace(content="Contextualized memory query")

        fake_chain = MagicMock()
        fake_chain.ainvoke = fake_ainvoke

        monkeypatch.setattr(
            "app.services.query_answering_workflow"
            ".ChatPromptTemplate.from_messages",
            lambda msgs: MagicMock(__or__=lambda self, other: fake_chain),
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow.LLMFactory.create",
            lambda: MagicMock(),
        )

        state: GraphState = {
            "query": "do you remember me?",
            "chat_history": [],
            "intent": "memory_query",
            "contextualize_prompt_str": "prompt",
        }

        new_state = await contextualize_node(state)
        assert "qa_prompt_str" in new_state
        assert "Use the provided Chat History" in new_state["qa_prompt_str"]
        assert "{context}" in new_state["qa_prompt_str"]
