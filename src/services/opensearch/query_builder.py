"""BM25 query builder for arXiv paper search."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PaperQueryBuilder:
    """
    Query builder for arXiv papers search.

    Builds complete OpenSearch queries with BM25 scoring, field boosting,
    category filtering, highlighting, and configurable sort order.
    """

    def __init__(
        self,
        query: str,
        size: int = 10,
        from_: int = 0,
        fields: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        track_total_hits: bool = True,
        latest_papers: bool = False,
    ):
        """Initialize query builder.

        :param query: Search query text
        :param size: Number of results to return
        :param from_: Offset for pagination
        :param fields: Fields to search in (with optional boost suffixes)
        :param categories: Filter by categories
        :param track_total_hits: Whether to track total hits accurately
        :param latest_papers: Sort by publication date instead of relevance
        """
        self.query = query
        self.size = size
        self.from_ = from_
        # Multi-field search with boosting: title (3x), abstract (2x), authors (1x)
        self.fields = fields or ["title^3", "abstract^2", "authors^1"]
        self.categories = categories
        self.track_total_hits = track_total_hits
        self.latest_papers = latest_papers

    def build(self) -> Dict[str, Any]:
        """Build the complete OpenSearch query body.

        :returns: Complete query dictionary ready for OpenSearch
        :rtype: Dict[str, Any]
        """
        query_body: Dict[str, Any] = {
            "query": self._build_query(),
            "size": self.size,
            "from": self.from_,
            "track_total_hits": self.track_total_hits,
            "_source": self._build_source_fields(),
            "highlight": self._build_highlight(),
        }

        sort = self._build_sort()
        if sort:
            query_body["sort"] = sort

        return query_body

    def _build_query(self) -> Dict[str, Any]:
        """Build the main bool query with optional filters.

        :returns: Query dict with bool structure
        :rtype: Dict[str, Any]
        """
        must_clauses: List[Dict[str, Any]] = []

        if self.query.strip():
            must_clauses.append(self._build_text_query())

        filter_clauses = self._build_filters()

        bool_query: Dict[str, Any] = {}
        bool_query["must"] = must_clauses if must_clauses else [{"match_all": {}}]

        if filter_clauses:
            bool_query["filter"] = filter_clauses

        return {"bool": bool_query}

    def _build_text_query(self) -> Dict[str, Any]:
        """Build the multi-match BM25 text search query.

        :returns: multi_match query dict
        :rtype: Dict[str, Any]
        """
        return {
            "multi_match": {
                "query": self.query,
                "fields": self.fields,
                "type": "best_fields",
                "operator": "or",
                "fuzziness": "AUTO",
                "prefix_length": 2,
            }
        }

    def _build_filters(self) -> List[Dict[str, Any]]:
        """Build filter clauses for the bool query.

        :returns: List of filter clause dicts
        :rtype: List[Dict[str, Any]]
        """
        filters: List[Dict[str, Any]] = []

        if self.categories:
            filters.append({"terms": {"categories": self.categories}})

        return filters

    def _build_source_fields(self) -> List[str]:
        """Define which fields to return in search results.

        :returns: List of field names to include in response
        :rtype: List[str]
        """
        return ["arxiv_id", "title", "authors", "abstract", "categories", "published_date", "pdf_url"]

    def _build_highlight(self) -> Dict[str, Any]:
        """Build highlighting configuration.

        :returns: Highlight configuration dictionary
        :rtype: Dict[str, Any]
        """
        return {
            "fields": {
                "title": {
                    "fragment_size": 0,       # Return the entire field
                    "number_of_fragments": 0,
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                },
                "abstract": {
                    "fragment_size": 150,
                    "number_of_fragments": 3,
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                },
                "authors": {
                    "fragment_size": 0,       # Return the entire field
                    "number_of_fragments": 0,
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                },
            },
            "require_field_match": False,
        }

    def _build_sort(self) -> Optional[List[Any]]:
        """Build sorting configuration.

        Returns date-descending sort for ``latest_papers`` or empty queries,
        and ``None`` (score sort) for normal text queries.

        :returns: Sort configuration or None for relevance scoring
        :rtype: Optional[List[Any]]
        """
        if self.latest_papers:
            return [{"published_date": {"order": "desc"}}, "_score"]

        if self.query.strip():
            return None  # Let OpenSearch use _score (BM25)

        # Empty query — sort newest first
        return [{"published_date": {"order": "desc"}}, "_score"]


def build_search_query(
    query: str,
    size: int = 10,
    from_: int = 0,
    categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Convenience helper to build a search query.

    :param query: Search query text
    :param size: Number of results
    :param from_: Offset for pagination
    :param categories: Optional category filter
    :returns: Search query dictionary
    :rtype: Dict[str, Any]
    """
    builder = PaperQueryBuilder(query=query, size=size, from_=from_, categories=categories)
    return builder.build()
