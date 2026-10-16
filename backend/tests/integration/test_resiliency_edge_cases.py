import pytest
import base64
import json
from unittest.mock import AsyncMock, MagicMock
from app.services.utils.history_utils import strip_context_prefixes
from app.services.query_answering_workflow import (
    run_mcp_tool_node,
    GraphState,
)


class TestResiliencyEdgeCases:

    def test_strip_context_prefixes_large_payload(self):
        """
        Verify that even a massive context prefix is correctly stripped.
        This simulates the 'context_length_exceeded' scenario.
        """
        # Create a large dummy context (e.g. 50KB)
        large_context = {
            "context": [{"page_content": "A" * 50000, "metadata": {}}]
        }
        b64_prefix = base64.b64encode(
            json.dumps(large_context).encode()
        ).decode()
        separator = "__LLM_RESPONSE__"
        actual_answer = "This is the actual answer."

        messages = [
            {"role": "user", "content": "How do I do X?"},
            {
                "role": "assistant",
                "content": f"{b64_prefix}{separator}{actual_answer}",
            },
        ]

        # Act
        cleaned = strip_context_prefixes(messages)

        # Assert
        assert cleaned[1]["content"] == actual_answer
        # Verify the large prefix is truly gone
        assert b64_prefix[:10] not in cleaned[1]["content"]

    @pytest.mark.asyncio
    async def test_run_mcp_tool_node_resiliency_on_upstream_error(self):
        """
        Verify that run_mcp_tool_node handles incoming error in state safely
        without executing retrieval.
        """
        # Arrange: state with an upstream error
        state: GraphState = {
            "query": "Where is my data?",
            "error": "LLM failed to contextualize",
        }

        # Act
        result = await run_mcp_tool_node(state)

        # Assert: It should return early because error is set.
        assert result["error"] == "LLM failed to contextualize"
        # The key should NOT cause a crash

    @pytest.mark.asyncio
    async def test_run_mcp_tool_node_resiliency_on_invalid_scope(self):
        """
        Verify that run_mcp_tool_node handles missing server_name/tool_name
        safely.
        """
        # Arrange: state with an error and a broken scope
        state: GraphState = {
            "query": "Where is my data?",
            "scope": {},  # Missing server_name/tool_name
            "error": "Previous node failed",
        }

        # Act
        result = await run_mcp_tool_node(state)

        # Assert: Should skip execution and return state
        assert result["error"] == "Previous node failed"

    @pytest.mark.asyncio
    async def test_run_mcp_tool_node_validation_error(self, monkeypatch):
        """
        Verify that run_mcp_tool_node handles dispatcher exceptions gracefully
        and sets the error in state.
        """
        fake_dispatcher = MagicMock()
        fake_dispatcher.call_tool = AsyncMock(
            side_effect=ValueError("Invalid retrieval parameters")
        )
        monkeypatch.setattr(
            "app.services.query_answering_workflow._mcp_dispatcher",
            fake_dispatcher,
        )

        state: GraphState = {
            "query": "Where is my data?",
            "knowledge_base_ids": [1],
        }

        # Act
        result = await run_mcp_tool_node(state)

        # Assert: It should catch the ValueError and set the error state
        assert "error" in result
        assert "Invalid retrieval parameters" in result["error"]
