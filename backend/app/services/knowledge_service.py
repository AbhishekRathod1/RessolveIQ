import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix

from app.ai.providers import ResolutionProvider
from app.schemas.knowledge import (
    KnowledgeCatalogResponse,
    KnowledgeDocumentSummary,
    KnowledgeMatch,
    KnowledgeSearchResponse,
    ResolutionStep,
    ResolutionSuggestionRequest,
    ResolutionSuggestionResponse,
    SupportingSource,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_BASE_DIR = REPOSITORY_ROOT / "data" / "knowledge_base"
MAX_CHUNK_CHARACTERS = 900
CHUNK_OVERLAP_CHARACTERS = 120
MIN_RELIABLE_SCORE = 0.12
MAX_SUGGESTION_STEPS = 5

SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"""(?i)\b(api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|"""
    r"""password|passwd|secret|token)\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,;]+)"""
)
SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?"
        r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.DOTALL,
    ),
)
STEP_PATTERN = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+(.+?)\s*$")
PRIVILEGED_CUES = (
    "password",
    "account",
    "access",
    "permission",
    "lockout",
    "security",
    "incident",
    "credential",
    "mfa",
)


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    title: str
    category: str
    content: str
    revision_date: date
    source_reference: str


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    title: str
    category: str
    content: str
    revision_date: date
    source_reference: str


@dataclass(frozen=True)
class ScoredChunk:
    chunk: KnowledgeChunk
    score: float


@dataclass(frozen=True)
class KnowledgeIndex:
    documents: tuple[KnowledgeDocument, ...]
    chunks: tuple[KnowledgeChunk, ...]
    vectorizer: TfidfVectorizer | None
    matrix: csr_matrix | None


def redact_sensitive_text(text: str) -> str:
    redacted = SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        text,
    )
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _metadata_key(key: str) -> str:
    return " ".join(key.strip().lower().replace("_", " ").split())


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_markdown(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)(.*)\Z", text, re.DOTALL)
    if match is None:
        raise ValueError("Markdown knowledge articles must begin with YAML-style metadata")
    metadata_text, content = match.groups()
    metadata: dict[str, str] = {}
    for line in metadata_text.splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"Malformed metadata line: {line}")
        normalized_key = _metadata_key(key)
        if normalized_key in metadata:
            raise ValueError(f"Duplicate metadata field: {key}")
        metadata[normalized_key] = _unquote(value)
    return metadata, content.strip()


def _parse_text_file(text: str) -> tuple[dict[str, str], str]:
    metadata: dict[str, str] = {}
    content_lines: list[str] = []
    reading_content = False
    for line in text.splitlines():
        if not reading_content:
            key, separator, value = line.partition(":")
            if separator:
                normalized_key = _metadata_key(key)
                if normalized_key == "content":
                    reading_content = True
                    if value.strip():
                        content_lines.append(value.strip())
                else:
                    if normalized_key in metadata:
                        raise ValueError(f"Duplicate metadata field: {key}")
                    metadata[normalized_key] = value.strip()
                continue
            if not line.strip():
                continue
            raise ValueError(f"Malformed text knowledge metadata line: {line}")
        content_lines.append(line)
    if not reading_content:
        raise ValueError("Text knowledge articles must include a Content: section")
    return metadata, "\n".join(content_lines).strip()


def parse_document(path: Path, text: str) -> KnowledgeDocument:
    if path.suffix.casefold() in {".md", ".markdown"}:
        metadata, content = _parse_markdown(text)
    elif path.suffix.casefold() == ".txt":
        metadata, content = _parse_text_file(text)
    else:
        raise ValueError(f"Unsupported knowledge file type: {path.suffix}")

    required = {
        "document id",
        "title",
        "category",
        "revision date",
        "source reference",
    }
    missing = required - metadata.keys()
    if missing:
        raise ValueError(f"Missing metadata in {path.name}: {', '.join(sorted(missing))}")
    empty = [key for key in required if not metadata[key].strip()]
    if empty:
        raise ValueError(f"Empty metadata in {path.name}: {', '.join(sorted(empty))}")
    if not content:
        raise ValueError(f"Knowledge article has no content: {path.name}")

    return KnowledgeDocument(
        document_id=redact_sensitive_text(metadata["document id"]),
        title=redact_sensitive_text(metadata["title"]),
        category=redact_sensitive_text(metadata["category"]),
        content=redact_sensitive_text(content),
        revision_date=date.fromisoformat(metadata["revision date"]),
        source_reference=redact_sensitive_text(metadata["source reference"]),
    )


def load_documents(directory: Path = KNOWLEDGE_BASE_DIR) -> tuple[KnowledgeDocument, ...]:
    if not directory.is_dir():
        return ()
    paths = sorted(
        (
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.casefold() in {".md", ".markdown", ".txt"}
        ),
        key=lambda path: path.relative_to(directory).as_posix().casefold(),
    )
    documents = tuple(
        parse_document(path, path.read_text(encoding="utf-8")) for path in paths
    )
    identifiers = [document.document_id for document in documents]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Knowledge document IDs must be unique")
    return documents


def _split_long_paragraph(paragraph: str) -> list[str]:
    parts: list[str] = []
    start = 0
    while start < len(paragraph):
        end = min(start + MAX_CHUNK_CHARACTERS, len(paragraph))
        if end < len(paragraph):
            boundary = paragraph.rfind(" ", start + MAX_CHUNK_CHARACTERS // 2, end)
            if boundary > start:
                end = boundary
        parts.append(paragraph[start:end].strip())
        if end == len(paragraph):
            break
        start = max(start + 1, end - CHUNK_OVERLAP_CHARACTERS)
    return parts


def chunk_content(content: str) -> tuple[str, ...]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", content) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > MAX_CHUNK_CHARACTERS:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_long_paragraph(paragraph))
            continue
        combined = f"{current}\n\n{paragraph}" if current else paragraph
        if len(combined) <= MAX_CHUNK_CHARACTERS:
            current = combined
        else:
            chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return tuple(chunks)


def build_index(documents: Sequence[KnowledgeDocument]) -> KnowledgeIndex:
    chunks = tuple(
        KnowledgeChunk(
            chunk_id=f"{document.document_id}#chunk-{number:02d}",
            document_id=document.document_id,
            title=document.title,
            category=document.category,
            content=content,
            revision_date=document.revision_date,
            source_reference=document.source_reference,
        )
        for document in documents
        for number, content in enumerate(chunk_content(document.content), start=1)
    )
    if not chunks:
        return KnowledgeIndex(tuple(documents), (), None, None)

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    texts = [
        f"{chunk.title}\n{chunk.category}\n{chunk.content}" for chunk in chunks
    ]
    matrix = vectorizer.fit_transform(texts)
    return KnowledgeIndex(tuple(documents), chunks, vectorizer, matrix)


@lru_cache(maxsize=1)
def get_knowledge_index() -> KnowledgeIndex:
    return build_index(load_documents(KNOWLEDGE_BASE_DIR))


def _search_index(
    index: KnowledgeIndex, query: str, top_k: int
) -> tuple[Literal["reliable_match", "no_reliable_match", "no_documents"], list[ScoredChunk]]:
    if not index.chunks or index.vectorizer is None or index.matrix is None:
        return "no_documents", []

    sanitized_query = redact_sensitive_text(query)
    query_vector = index.vectorizer.transform([sanitized_query])
    scores = cosine_similarity(query_vector, index.matrix).ravel()
    ranked_indices = sorted(
        range(len(index.chunks)),
        key=lambda index_number: (
            -float(scores[index_number]),
            index.chunks[index_number].chunk_id,
        ),
    )
    if not ranked_indices or float(scores[ranked_indices[0]]) < MIN_RELIABLE_SCORE:
        return "no_reliable_match", []

    matches = [
        ScoredChunk(index.chunks[index_number], float(scores[index_number]))
        for index_number in ranked_indices[:top_k]
        if float(scores[index_number]) >= MIN_RELIABLE_SCORE
    ]
    return "reliable_match", matches


def list_knowledge() -> KnowledgeCatalogResponse:
    index = get_knowledge_index()
    items = [
        KnowledgeDocumentSummary(
            document_id=document.document_id,
            title=document.title,
            category=document.category,
            revision_date=document.revision_date,
            source_reference=document.source_reference,
        )
        for document in index.documents
    ]
    return KnowledgeCatalogResponse(items=items, total=len(items))


def search_knowledge(query: str, top_k: int = 5) -> KnowledgeSearchResponse:
    index = get_knowledge_index()
    state, scored_chunks = _search_index(index, query, top_k)
    matches = [
        KnowledgeMatch(
            chunk_id=entry.chunk.chunk_id,
            document_id=entry.chunk.document_id,
            title=entry.chunk.title,
            category=entry.chunk.category,
            revision_date=entry.chunk.revision_date,
            source_reference=entry.chunk.source_reference,
            content=entry.chunk.content,
            similarity_score=entry.score,
        )
        for entry in scored_chunks
    ]
    return KnowledgeSearchResponse(
        state=state,
        matches=matches,
        minimum_reliable_score=MIN_RELIABLE_SCORE,
    )


class ExtractiveResolutionProvider:
    def suggest(
        self, issue_summary: str, evidence: Sequence[KnowledgeChunk]
    ) -> list[ResolutionStep]:
        del issue_summary
        steps: list[ResolutionStep] = []
        seen: set[str] = set()
        for chunk in evidence:
            for line in chunk.content.splitlines():
                match = STEP_PATTERN.match(line)
                if match is None:
                    continue
                text = redact_sensitive_text(match.group(1).strip())
                normalized = " ".join(text.casefold().split())
                if normalized in seen:
                    continue
                seen.add(normalized)
                steps.append(
                    ResolutionStep(
                        text=text,
                        document_id=chunk.document_id,
                        source_reference=chunk.source_reference,
                    )
                )
                if len(steps) >= MAX_SUGGESTION_STEPS:
                    return steps
        return steps


def _issue_summary(request: ResolutionSuggestionRequest) -> str:
    summary = " ".join(
        redact_sensitive_text(f"{request.title}. {request.description}").split()
    )
    if len(summary) > 400:
        return summary[:397].rstrip() + "..."
    return summary


def _supporting_sources(
    scored_chunks: Sequence[ScoredChunk],
) -> list[SupportingSource]:
    grouped: dict[str, SupportingSource] = {}
    for entry in scored_chunks:
        chunk = entry.chunk
        source = grouped.get(chunk.document_id)
        if source is None:
            source = SupportingSource(
                document_id=chunk.document_id,
                title=chunk.title,
                category=chunk.category,
                revision_date=chunk.revision_date,
                source_reference=chunk.source_reference,
                chunk_ids=[],
                retrieval_score=entry.score,
            )
            grouped[chunk.document_id] = source
        if chunk.chunk_id not in source.chunk_ids:
            source.chunk_ids.append(chunk.chunk_id)
        source.retrieval_score = max(source.retrieval_score, entry.score)
    return list(grouped.values())


def suggest_resolution(
    request: ResolutionSuggestionRequest,
    provider: ResolutionProvider | None = None,
) -> ResolutionSuggestionResponse:
    summary = _issue_summary(request)
    index = get_knowledge_index()
    state, scored_chunks = _search_index(
        index,
        f"{request.title}\n{request.description}",
        request.top_k,
    )
    evidence = [entry.chunk for entry in scored_chunks]
    resolution_provider = provider or ExtractiveResolutionProvider()
    steps = resolution_provider.suggest(summary, evidence) if evidence else []
    sources = _supporting_sources(scored_chunks)
    sufficient_evidence = state == "reliable_match" and bool(steps)

    if sufficient_evidence:
        evidence_state: Literal["suggested", "insufficient_evidence"] = "suggested"
        warning = (
            "Retrieval scores are raw cosine similarities, not probabilities or "
            "calibrated confidence. Verify the cited guidance before acting."
        )
    else:
        evidence_state = "insufficient_evidence"
        steps = []
        warning = (
            "Insufficient reliable knowledge-base evidence was found. No "
            "troubleshooting instructions were generated."
        )

    privileged_topic = any(
        cue in f"{request.title} {request.description}".casefold()
        for cue in PRIVILEGED_CUES
    ) or any(source.category.casefold() in {"security", "account & access"} for source in sources)
    manual_review_reason = (
        "Every suggestion requires human review. This issue may involve "
        "privileged account or security handling; only authorized staff should "
        "perform such actions using approved procedures."
        if privileged_topic
        else "Every extractive suggestion requires human verification before it is followed."
    )

    return ResolutionSuggestionResponse(
        evidence_state=evidence_state,
        issue_summary=summary,
        recommended_steps=steps,
        supporting_sources=sources,
        confidence_warning=warning,
        manual_review_required=True,
        manual_review_reason=manual_review_reason,
    )
