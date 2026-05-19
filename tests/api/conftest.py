from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Async backend for testing."""
    return "asyncio"


@pytest.fixture
async def client():
    """HTTP client for API testing with mocked external services.

    Patches all external service connections so tests run without
    a live PostgreSQL, OpenSearch, Ollama, or arXiv instance.
    """
    with (
        patch("src.db.interfaces.postgresql.PostgreSQLDatabase.startup") as mock_startup,
        patch("src.db.interfaces.postgresql.PostgreSQLDatabase.get_session") as mock_get_session,
        patch("src.main.make_opensearch_client") as mock_os_factory,
        patch("src.main.make_arxiv_client") as mock_arxiv,
        patch("src.main.make_pdf_parser_service") as mock_pdf,
        patch("src.services.ollama.client.OllamaClient") as mock_ollama,
        patch("src.repositories.paper.PaperRepository.get_by_arxiv_id") as mock_get_by_id,
    ):
        # Database mocks
        mock_startup.return_value = None
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)
        mock_get_by_id.return_value = None

        # OpenSearch mock — healthy by default, returns empty search results
        mock_os_client = MagicMock()
        mock_os_client.health_check.return_value = True
        mock_os_client.create_index.return_value = False   # already exists
        mock_os_client.get_index_stats.return_value = {
            "index_name": "arxiv-papers",
            "document_count": 42,
            "health": "green",
        }
        mock_os_client.search_papers.return_value = {"total": 0, "hits": []}
        mock_os_factory.return_value = mock_os_client

        # Other service mocks
        mock_arxiv.return_value = AsyncMock()
        mock_pdf.return_value = AsyncMock()
        mock_ollama.return_value = AsyncMock()

        async with LifespanManager(app) as manager:
            async with AsyncClient(
                transport=ASGITransport(app=manager.app), base_url="http://test"
            ) as ac:
                yield ac
