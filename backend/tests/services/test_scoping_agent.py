import json
import pytest

from app.services.scoping_agent import ScopingAgent


@pytest.mark.unit
@pytest.mark.asyncio
class TestScopingAgent:
    """Unit tests for ScopingAgent."""

    @pytest.fixture
    def discovery_file(self, tmp_path):
        """Fixture to create a temporary discovery file path."""
        return tmp_path / "mcp_discovery.json"

    @pytest.fixture
    def valid_discovery_data(self):
        """Fixture with valid discovery data containing the required tool."""
        return {
            "tools": {
                "knowledge_bases_mcp": [
                    {
                        "name": "query_knowledge_base",
                        "description": "desc",
                        "inputSchema": {},
                    }
                ]
            },
            "resources": {},
        }

    @pytest.fixture
    def agent(self, discovery_file):
        """Fixture to create ScopingAgent instance with temp discovery file."""
        return ScopingAgent(discovery_file=str(discovery_file))

    # -------------------- Success scenarios --------------------

    def test_load_discovery_data_success(
        self, agent, discovery_file, valid_discovery_data
    ):
        """load_discovery_data() returns parsed JSON when file exists."""
        discovery_file.write_text(json.dumps(valid_discovery_data))

        data = agent.load_discovery_data()
        assert "tools" in data
        assert "knowledge_bases_mcp" in data["tools"]

    async def test_scope_query_success(
        self, agent, discovery_file, valid_discovery_data, monkeypatch
    ):
        """
        scope_query() returns scoped tool execution info when tool exists.
        """
        discovery_file.write_text(json.dumps(valid_discovery_data))

        # Async mock of _ask_llm
        async def fake__ask_llm(query, data, scope):
            return {
                "server_name": "knowledge_bases_mcp",
                "tool_name": "query_knowledge_base",
                "input": {
                    "knowledge_base_ids": scope["knowledge_base_ids"],
                    "query": query,
                    "top_k": scope["top_k"],
                },
            }

        monkeypatch.setattr(agent, "_ask_llm", fake__ask_llm)

        result = await agent.scope_query(
            "find documents", scope={"knowledge_base_ids": [42], "top_k": 5}
        )

        assert result["server_name"] == "knowledge_bases_mcp"
        assert result["tool_name"] == "query_knowledge_base"
        assert result["input"] == {
            "knowledge_base_ids": [42],
            "query": "find documents",
            "top_k": 5,
        }

    # -------------------- Error scenarios --------------------

    def test_load_discovery_data_file_not_found(self, agent):
        """
        load_discovery_data() raises FileNotFoundError if file does not exist.
        """
        with pytest.raises(FileNotFoundError):
            agent.load_discovery_data()

    async def test_scope_query_tool_not_found(
        self, agent, discovery_file, monkeypatch
    ):
        """
        scope_query() raises ValueError if required tool
        is missing or LLM fails.
        """
        invalid_data = {"tools": {"knowledge_bases_mcp": []}, "resources": {}}
        discovery_file.write_text(json.dumps(invalid_data))

        # Async mock to simulate no suggestion from LLM
        async def fake__ask_llm(*_, **__):
            return None

        monkeypatch.setattr(agent, "_ask_llm", fake__ask_llm)

        with pytest.raises(
            ValueError, match="did not return a valid suggestion"
        ):
            await agent.scope_query(query="find documents")
