from typing import List, Dict


def strip_context_prefixes(messages: List[Dict]) -> List[Dict]:
    """
    Sanitize chat history by removing internal context prefixes.
    The prefix is base64-encoded search metadata followed by '__LLM_RESPONSE__'.
    """
    cleaned = []
    for msg in messages:
        content = msg.get("content", "")
        if "__LLM_RESPONSE__" in content:
            # Strip everything before and including the delimiter
            content = content.split("__LLM_RESPONSE__")[-1]

        cleaned.append({**msg, "content": content})
    return cleaned
