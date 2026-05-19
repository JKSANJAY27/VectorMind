"""OpenSearch client for arXiv paper indexing and BM25 search."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError, RequestError
from src.config import Settings, get_settings

from .index_config import ARXIV_PAPERS_INDEX, ARXIV_PAPERS_MAPPING
from .query_builder import PaperQueryBuilder

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """
    Client for OpenSearch operations including index management and BM25 search.

    Provides methods for creating indices, indexing papers, searching with BM25
    scoring, and managing OpenSearch cluster operations.
    """

    def __init__(self, host: str = "http://localhost:9200", settings: Optional[Settings] = None):
        """Initialize OpenSearch client.

        :param host: OpenSearch cluster endpoint URL
        :param settings: Application settings instance (uses default if None)
        :type host: str
        :type settings: Optional[Settings]
        """
        self.host = host
        self.settings = settings or get_settings()
        self.index_name = self.settings.opensearch.index_name or ARXIV_PAPERS_INDEX
        self.client = OpenSearch(
            hosts=[host],
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )
        logger.info(f"OpenSearch client initialized with host: {host}, index: {self.index_name}")

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def create_index(self, force: bool = False) -> bool:
        """Create the arxiv-papers index with proper mappings.

        :param force: If True, delete existing index before creating
        :type force: bool
        :returns: True if index was created, False if it already exists
        :rtype: bool
        """
        try:
            if self.client.indices.exists(index=self.index_name):
                if force:
                    logger.info(f"Deleting existing index: {self.index_name}")
                    self.client.indices.delete(index=self.index_name)
                else:
                    logger.info(f"Index '{self.index_name}' already exists — skipping creation")
                    return False

            response = self.client.indices.create(index=self.index_name, body=ARXIV_PAPERS_MAPPING)

            if response.get("acknowledged"):
                logger.info(f"Successfully created index: {self.index_name}")
                return True
            else:
                logger.error(f"Failed to create index: {response}")
                return False

        except RequestError as e:
            logger.error(f"RequestError creating index: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating index: {e}")
            return False

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_paper(self, paper_data: Dict[str, Any]) -> bool:
        """Index (upsert) a single paper document.

        :param paper_data: Paper data to index; must contain 'arxiv_id'
        :type paper_data: Dict[str, Any]
        :returns: True if successful, False otherwise
        :rtype: bool
        """
        try:
            if "arxiv_id" not in paper_data:
                logger.error("Missing arxiv_id in paper data — skipping")
                return False

            # Add timestamps if absent
            now = datetime.now(timezone.utc).isoformat()
            paper_data.setdefault("created_at", now)
            paper_data.setdefault("updated_at", now)

            # Normalise authors to string
            if isinstance(paper_data.get("authors"), list):
                paper_data["authors"] = ", ".join(paper_data["authors"])

            response = self.client.index(
                index=self.index_name,
                id=paper_data["arxiv_id"],
                body=paper_data,
                refresh=True,  # Immediately searchable
            )

            if response.get("result") in ["created", "updated"]:
                logger.debug(f"Indexed paper: {paper_data['arxiv_id']} ({response['result']})")
                return True
            else:
                logger.error(f"Unexpected index response for {paper_data['arxiv_id']}: {response}")
                return False

        except Exception as e:
            logger.error(f"Error indexing paper {paper_data.get('arxiv_id', 'unknown')}: {e}")
            return False

    def bulk_index_papers(self, papers: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk index multiple papers.

        :param papers: List of paper data dicts to index
        :type papers: List[Dict[str, Any]]
        :returns: Dictionary with 'success' and 'failed' counts
        :rtype: Dict[str, int]
        """
        results = {"success": 0, "failed": 0}

        for paper in papers:
            if self.index_paper(paper):
                results["success"] += 1
            else:
                results["failed"] += 1

        logger.info(f"Bulk indexing complete: {results['success']} succeeded, {results['failed']} failed")
        return results

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_papers(
        self,
        query: str,
        size: int = 10,
        from_: int = 0,
        fields: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        track_total_hits: bool = True,
        latest_papers: bool = False,
    ) -> Dict[str, Any]:
        """Search papers using BM25 scoring via PaperQueryBuilder.

        :param query: Search query text
        :param size: Number of results to return
        :param from_: Offset for pagination
        :param fields: Fields to search in (default: title^3, abstract^2, authors^1)
        :param categories: Filter by categories
        :param track_total_hits: Whether to track total hits accurately
        :param latest_papers: Sort by publication date instead of relevance
        :type query: str
        :type size: int
        :type from_: int
        :type fields: Optional[List[str]]
        :type categories: Optional[List[str]]
        :type track_total_hits: bool
        :type latest_papers: bool
        :returns: Dict with 'total' and 'hits' list
        :rtype: Dict[str, Any]
        """
        try:
            query_builder = PaperQueryBuilder(
                query=query,
                size=size,
                from_=from_,
                fields=fields,
                categories=categories,
                track_total_hits=track_total_hits,
                latest_papers=latest_papers,
            )
            search_body = query_builder.build()

            response = self.client.search(index=self.index_name, body=search_body)

            results: Dict[str, Any] = {
                "total": response["hits"]["total"]["value"],
                "hits": [],
            }

            for hit in response["hits"]["hits"]:
                paper = hit["_source"].copy()
                paper["score"] = hit["_score"]
                if "highlight" in hit:
                    paper["highlights"] = hit["highlight"]
                results["hits"].append(paper)

            logger.info(f"Search '{query}' → {results['total']} total hits ({len(results['hits'])} returned)")
            return results

        except NotFoundError:
            logger.error(f"Index '{self.index_name}' not found")
            return {"total": 0, "hits": [], "error": "Index not found"}
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"total": 0, "hits": [], "error": str(e)}

    # ------------------------------------------------------------------
    # Stats & health
    # ------------------------------------------------------------------

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the OpenSearch index.

        :returns: Dict with index_name, document_count, size_in_bytes, health
        :rtype: Dict[str, Any]
        """
        try:
            stats = self.client.indices.stats(index=self.index_name)
            count = self.client.count(index=self.index_name)

            return {
                "index_name": self.index_name,
                "document_count": count["count"],
                "size_in_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                "health": self.client.cluster.health(index=self.index_name)["status"],
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {"error": str(e)}

    def health_check(self) -> bool:
        """Check if OpenSearch is healthy and accessible.

        :returns: True if cluster status is green or yellow
        :rtype: bool
        """
        try:
            health = self.client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"OpenSearch health check failed: {e}")
            return False

    def get_cluster_info(self) -> Optional[Dict[str, Any]]:
        """Get raw OpenSearch cluster information.

        :returns: Cluster info dict or None on error
        :rtype: Optional[Dict[str, Any]]
        """
        try:
            return self.client.info()
        except Exception as e:
            logger.error(f"Error getting cluster info: {e}")
            return None

    def get_cluster_health(self) -> Optional[Dict[str, Any]]:
        """Get detailed cluster health information.

        :returns: Cluster health dict or None on error
        :rtype: Optional[Dict[str, Any]]
        """
        try:
            return self.client.cluster.health()
        except Exception as e:
            logger.error(f"Error getting cluster health: {e}")
            return None

    def get_index_mapping(self) -> Optional[Dict[str, Any]]:
        """Get index mapping for introspection.

        :returns: Mapping dict or None on error
        :rtype: Optional[Dict[str, Any]]
        """
        try:
            mappings = self.client.indices.get_mapping(index=self.index_name)
            if mappings and self.index_name in mappings:
                return mappings[self.index_name].get("mappings", {})
            return {}
        except Exception as e:
            logger.error(f"Error getting index mapping: {e}")
            return None

    def get_index_settings(self) -> Optional[Dict[str, Any]]:
        """Get index settings for introspection.

        :returns: Settings dict or None on error
        :rtype: Optional[Dict[str, Any]]
        """
        try:
            settings = self.client.indices.get_settings(index=self.index_name)
            if settings and self.index_name in settings:
                return settings[self.index_name].get("settings", {})
            return {}
        except Exception as e:
            logger.error(f"Error getting index settings: {e}")
            return None
