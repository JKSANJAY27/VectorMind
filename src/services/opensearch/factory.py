"""Factory for creating a cached OpenSearch client instance."""

from functools import lru_cache

from src.config import get_settings

from .client import OpenSearchClient


@lru_cache(maxsize=1)
def make_opensearch_client() -> OpenSearchClient:
    """Factory function that returns a singleton OpenSearch client.

    Uses ``lru_cache`` to maintain a single instance per process, consistent
    with other service factories (arxiv, pdf_parser, database).

    :returns: Cached OpenSearchClient instance
    :rtype: OpenSearchClient
    """
    settings = get_settings()
    return OpenSearchClient(host=settings.opensearch.host, settings=settings)
