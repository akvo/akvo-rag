import pytest
import base64
import json
from app.services.utils.history_utils import strip_context_prefixes
from app.services.query_answering_workflow import (
    scoping_node,
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
    async def test_scoping_node_resiliency_on_missing_query(self):
        """
        Verify that scoping_node handles missing 'contextual_query'
        safely.
        """
        # Arrange: state without 'contextual_query', simulating a failure in
        # 'contextualize_node'
        state: GraphState = {
            "query": "Where is my data?",
            "error": "LLM failed to contextualize",
        }

        # Act
        result = await scoping_node(state)

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
    async def test_run_mcp_tool_node_validation_error(self):
        """
        Verify that run_mcp_tool_node raises a proper error state if scope
        is invalid (and no prior error).
        """
        # Arrange: no prior error, but scope is missing required keys
        state: GraphState = {
            "query": "Where is my data?",
            "scope": {"input": {}},  # Missing server_name and tool_name
        }

        # Act
        result = await run_mcp_tool_node(state)

        # Assert: It should catch the ValueError and set the error state
        assert "error" in result
        assert "Invalid scope" in result["error"]
