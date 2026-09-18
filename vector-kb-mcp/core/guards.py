from typing import List
from .exceptions import EmbeddingDimensionMismatchError


def validate_embedding_dimension(
    embedding: List[float],
    expected_dim: int = 1536,
    kb_id: int = 0,
    model: str = "text-embedding-3-small",
) -> List[float]:
    """
    Validate that an embedding vector matches the required dimensionality.

    Args:
        embedding: List of float values representing the embedding vector.
        expected_dim: Expected dimension size (default: 1536).
        kb_id: Target knowledge base ID for contextual error reporting.
        model: Model identifier for contextual error reporting.

    Returns:
        The validated embedding vector if dimension matches.

    Raises:
        EmbeddingDimensionMismatchError: If len(embedding) != expected_dim.
    """
    actual_dim = len(embedding)
    if actual_dim != expected_dim:
        raise EmbeddingDimensionMismatchError(
            kb_id=kb_id,
            expected_dim=expected_dim,
            actual_dim=actual_dim,
            model=model,
        )
    return embedding
