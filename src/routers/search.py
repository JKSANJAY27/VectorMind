"""BM25 keyword search endpoint using OpenSearch."""

import logging

from fastapi import APIRouter, HTTPException
from src.dependencies import OpenSearchDep
from src.schemas.api.search import SearchHit, SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/", response_model=SearchResponse, summary="BM25 keyword search")
async def search_papers(request: SearchRequest, opensearch_client: OpenSearchDep) -> SearchResponse:
    """Search arXiv papers using BM25 scoring in OpenSearch.

    Searches across paper **titles** (3× boost), **abstracts** (2× boost),
    and **authors** (1× boost) using OpenSearch's built-in BM25 algorithm.

    Results are sorted by relevance score by default. Pass
    ``latest_papers=true`` to sort by publication date (newest first) instead.

    Supports optional pagination (``from`` / ``size``) and category filtering.

    :param request: Search request parameters
    :param opensearch_client: Injected OpenSearch client
    :returns: Ranked search results with highlights
    :rtype: SearchResponse
    :raises HTTPException 503: When OpenSearch is unavailable
    :raises HTTPException 500: On unexpected search errors
    """
    try:
        if not opensearch_client.health_check():
            raise HTTPException(status_code=503, detail="Search service is currently unavailable")

        logger.info(f"Searching: query='{request.query}' size={request.size} from={request.from_} latest={request.latest_papers}")

        results = opensearch_client.search_papers(
            query=request.query,
            size=request.size,
            from_=request.from_,
            categories=request.categories,
            latest_papers=request.latest_papers,
        )

        hits = [
            SearchHit(
                arxiv_id=hit.get("arxiv_id", ""),
                title=hit.get("title", ""),
                authors=hit.get("authors"),
                abstract=hit.get("abstract"),
                published_date=hit.get("published_date"),
                pdf_url=hit.get("pdf_url"),
                score=hit.get("score", 0.0),
                highlights=hit.get("highlights"),
            )
            for hit in results.get("hits", [])
        ]

        return SearchResponse(
            query=request.query,
            total=results.get("total", 0),
            hits=hits,
            error=results.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
