"""Pydantic schemas for the BM25 search API endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query across title, abstract, and authors",
    )
    size: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    from_: int = Field(default=0, ge=0, alias="from", description="Offset for pagination")
    categories: Optional[List[str]] = Field(default=None, description="Filter by arXiv categories")
    latest_papers: bool = Field(
        default=False,
        description="Sort by publication date (newest first) instead of relevance",
    )

    model_config = {"populate_by_name": True}


class SearchHit(BaseModel):
    """Individual search result hit."""

    arxiv_id: str
    title: str
    authors: Optional[str] = None
    abstract: Optional[str] = None
    published_date: Optional[str] = None
    pdf_url: Optional[str] = None
    score: float
    highlights: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response model."""

    query: str
    total: int
    hits: List[SearchHit]
    error: Optional[str] = None
