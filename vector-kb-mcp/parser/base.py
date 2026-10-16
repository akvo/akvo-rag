from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedDocument:
    file_name: str
    total_pages: int
    pages: List[ParsedPage]
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseDocumentParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str, file_name: str) -> ParsedDocument:
        """
        Parse raw file from filesystem into structured pages.

        Args:
            file_path: Absolute or relative path to the source file on disk.
            file_name: The original human-readable file name.

        Returns:
            ParsedDocument containing extracted pages and metadata.
        """
        pass
