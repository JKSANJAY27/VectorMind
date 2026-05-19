import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from src.config import get_settings
from src.db.factory import make_database
from src.routers import papers, ping, search
from src.services.arxiv.factory import make_arxiv_client
from src.services.opensearch.factory import make_opensearch_client
from src.services.pdf_parser.factory import make_pdf_parser_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the API."""
    logger.info("Starting RAG API...")

    settings = get_settings()
    app.state.settings = settings

    # Database
    database = make_database()
    app.state.database = database
    logger.info("Database connected")

    # OpenSearch
    opensearch_client = make_opensearch_client()
    app.state.opensearch_client = opensearch_client

    if opensearch_client.health_check():
        logger.info("OpenSearch connected successfully")
        if opensearch_client.create_index(force=False):
            logger.info("OpenSearch index created")
        else:
            logger.info("OpenSearch index already exists")
        stats = opensearch_client.get_index_stats()
        logger.info(f"OpenSearch ready: {stats.get('document_count', 0)} documents indexed")
    else:
        logger.warning("OpenSearch connection failed — search features will be limited")

    # arXiv client
    app.state.arxiv_client = make_arxiv_client()

    # PDF parser (optional dependency)
    try:
        app.state.pdf_parser = make_pdf_parser_service()
        logger.info("Services initialized: arXiv API client, PDF parser, OpenSearch")
    except ImportError as e:
        logger.warning(f"PDF parser NOT initialized (missing dependency): {e}")
        app.state.pdf_parser = None
        logger.info("Services initialized: arXiv API client, OpenSearch")

    logger.info("API ready")
    yield

    # Cleanup
    database.teardown()
    logger.info("API shutdown complete")


app = FastAPI(
    title="arXiv Paper Curator API",
    description="Personal arXiv CS.AI paper curator with RAG capabilities",
    version=os.getenv("APP_VERSION", "0.1.0"),
    lifespan=lifespan,
)

# Include routers
app.include_router(ping.router, prefix="/api/v1")
app.include_router(papers.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="0.0.0.0")
