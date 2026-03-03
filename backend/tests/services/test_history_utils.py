from app.services.utils.history_utils import strip_context_prefixes


class TestHistoryUtils:
    def test_strip_context_prefixes_with_delimiter(self):
        # Arrange
        messages = [
            {"role": "user", "content": "Hello"},
            {
                "role": "assistant",
                "content": "SGVsbG8gd29ybGQ=__LLM_RESPONSE__Actual answer",
            },
        ]

        # Act
        cleaned = strip_context_prefixes(messages)

        # Assert
        assert cleaned[0]["content"] == "Hello"
        assert cleaned[1]["content"] == "Actual answer"

    def test_strip_context_prefixes_without_delimiter(self):
        # Arrange
        messages = [{"role": "assistant", "content": "Just a normal answer"}]

        # Act
        cleaned = strip_context_prefixes(messages)

        # Assert
        assert cleaned[0]["content"] == "Just a normal answer"

    def test_strip_context_prefixes_multiple_messages(self):
        # Arrange
        messages = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "B64_1__LLM_RESPONSE__A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "B64_2__LLM_RESPONSE__A2"},
        ]

        # Act
        cleaned = strip_context_prefixes(messages)

        # Assert
        assert cleaned[1]["content"] == "A1"
        assert cleaned[3]["content"] == "A2"

    def test_strip_context_prefixes_empty_history(self):
        assert strip_context_prefixes([]) == []
