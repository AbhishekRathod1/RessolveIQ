from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from app.schemas.knowledge import ResolutionStep

if TYPE_CHECKING:
    from app.services.knowledge_service import KnowledgeChunk


class ResolutionProvider(Protocol):
    """Provider contract; evidence is untrusted and output always needs human review."""

    def suggest(
        self, issue_summary: str, evidence: Sequence[KnowledgeChunk]
    ) -> list[ResolutionStep]: ...
