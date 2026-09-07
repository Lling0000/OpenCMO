"""Wire-independent contracts shared by indexing, retrieval and generation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class TextBlock:
    start: int
    end: int
    heading: str = ""
    page: int | None = None
    kind: str = "paragraph"
    prefix: str = ""


@dataclass
class ParsedDocument:
    text: str
    blocks: list[TextBlock]
    parser_version: str = "1"


@dataclass
class Chunk:
    id: str
    parent_id: str | None
    level: str
    start: int
    end: int
    text: str
    heading: str = ""
    page: int | None = None
    prefix: str = ""


@dataclass
class RetrievalRequest:
    account_id: int
    project_id: int | None
    query: str
    purpose: str = "internal"
    mode: str = "auto"
    history: list[dict] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None
    lanes: tuple[str, ...] = ('dense', 'bm25', 'entity')
    use_reranker: bool = True


@dataclass
class Citation:
    id: str
    label: str
    document_id: str
    version_id: str
    chunk_id: str
    title: str
    quote: str
    start: int
    end: int
    heading: str = ""
    page: int | None = None
    generated: bool = False
    created_at: str = ""
    url: str = ""


@dataclass
class RetrievalHit:
    chunk_id: str
    document_id: str
    version_id: str
    parent_id: str | None
    title: str
    text: str
    start: int
    end: int
    heading: str = ""
    page: int | None = None
    generated: bool = False
    created_at: str = ""
    lanes: list[str] = field(default_factory=list)
    fusion_score: float = 0.0
    rerank_score: float | None = None


@dataclass
class RetrievalResult:
    retrieval_id: str
    hits: list[RetrievalHit] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    context: str = ""
    warnings: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    lane_results: dict[str, list[str]] = field(default_factory=dict)
    status: str = "empty"
    ranking: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
