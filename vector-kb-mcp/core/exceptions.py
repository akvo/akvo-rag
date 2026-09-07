class VectorMCPException(Exception):
    """Base exception for all vector-kb-mcp operations."""

    pass


class DocumentProcessingError(VectorMCPException):
    """Raised when document parsing, extraction, or processing fails."""

    pass


class SecurityValidationError(VectorMCPException):
    """
    Raised when a security boundary constraint (e.g. cross-tenant
    key access) is violated.
    """

    pass


class EmbeddingDimensionMismatchError(VectorMCPException):
    """
    Raised when an embedding vector's dimensionality does not match the
    expected dimensionality configured for a knowledge base or retriever.
    """

    def __init__(
        self,
        kb_id: int,
        expected_dim: int,
        actual_dim: int,
        model: str,
    ):
        self.kb_id = kb_id
        self.expected_dim = expected_dim
        self.actual_dim = actual_dim
        self.model = model
        super().__init__(
            f"Embedding dimension mismatch for KB #{kb_id} using model "
            f"'{model}'. Expected {expected_dim}-dim, received "
            f"{actual_dim}-dim."
        )
