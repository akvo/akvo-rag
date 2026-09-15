import hashlib
from typing import Any, Dict, Optional, Tuple


def generate_chunk_id(
    kb_id: int,
    file_name: str,
    chunk_content: str,
    chunk_metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """
    Generate a deterministic SHA256 content hash and unique chunk ID.

    Args:
        kb_id: The ID of the knowledge base.
        file_name: The source file name.
        chunk_content: The text content of the chunk.
        chunk_metadata: Optional dictionary of chunk metadata.

    Returns:
        Tuple of (content_hash_hex, chunk_id_string)
    """
    cleaned_content = chunk_content.strip()
    # 1. Content-based hash (64-char hex)
    content_hash = hashlib.sha256(cleaned_content.encode("utf-8")).hexdigest()

    # 2. Composite deterministic chunk ID
    composite_key = f"{kb_id}:{file_name}:{cleaned_content}"
    composite_bytes = composite_key.encode("utf-8")
    composite_digest = hashlib.sha256(composite_bytes).hexdigest()[:16]
    chunk_id = f"kb_{kb_id}_{composite_digest}"

    return content_hash, chunk_id
