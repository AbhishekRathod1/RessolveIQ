from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

KnowledgeQuery = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000)
]


class KnowledgeDocumentSummary(BaseModel):
    document_id: str
    title: str
    category: str
    revision_date: date
    source_reference: str


class KnowledgeCatalogResponse(BaseModel):
    items: list[KnowledgeDocumentSummary]
    total: int


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: KnowledgeQuery
    top_k: int = Field(default=5, ge=1, le=10)


class KnowledgeMatch(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    category: str
    revision_date: date
    source_reference: str
    content: str
    similarity_score: float
    score_type: Literal["raw_cosine_similarity"] = "raw_cosine_similarity"


class KnowledgeSearchResponse(BaseModel):
    state: Literal["reliable_match", "no_reliable_match", "no_documents"]
    matches: list[KnowledgeMatch]
    minimum_reliable_score: float


class ResolutionSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    description: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000),
    ]
    top_k: int = Field(default=3, ge=1, le=5)


class ResolutionStep(BaseModel):
    text: str
    document_id: str
    source_reference: str


class SupportingSource(BaseModel):
    document_id: str
    title: str
    category: str
    revision_date: date
    source_reference: str
    chunk_ids: list[str]
    retrieval_score: float
    score_type: Literal["raw_cosine_similarity"] = "raw_cosine_similarity"


class ResolutionSuggestionResponse(BaseModel):
    evidence_state: Literal["suggested", "insufficient_evidence"]
    issue_summary: str
    recommended_steps: list[ResolutionStep]
    supporting_sources: list[SupportingSource]
    confidence_warning: str
    manual_review_required: bool
    manual_review_reason: str
