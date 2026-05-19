from fastapi import APIRouter
from sqlalchemy import text

from ..dependencies import DatabaseDep, OpenSearchDep, SettingsDep
from ..exceptions import OllamaConnectionError, OllamaException, OllamaTimeoutError
from ..schemas.api.health import HealthResponse, ServiceStatus
from ..services.ollama import OllamaClient

router = APIRouter()


@router.get("/ping", tags=["Health"])
async def ping():
    """Simple ping endpoint for basic connectivity tests."""
    return {"status": "ok", "message": "pong"}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health and status of the API service including database, OpenSearch, and Ollama connectivity.",
    response_description="Service health information",
    tags=["Health"],
)
async def health_check(
    settings: SettingsDep,
    database: DatabaseDep,
    opensearch_client: OpenSearchDep,
) -> HealthResponse:
    """Comprehensive health check endpoint for monitoring and load balancer probes.

    Checks connectivity to PostgreSQL, OpenSearch, and Ollama. Reports overall
    status as ``ok`` (all healthy) or ``degraded`` (one or more services down).

    :param settings: Application settings
    :param database: Database instance
    :param opensearch_client: OpenSearch client
    :returns: Service health status with version and connectivity checks
    :rtype: HealthResponse
    """
    services = {}
    overall_status = "ok"

    # --- Database check ---
    try:
        with database.get_session() as session:
            session.execute(text("SELECT 1"))
        services["database"] = ServiceStatus(status="healthy", message="Connected successfully")
    except Exception as e:
        services["database"] = ServiceStatus(status="unhealthy", message=f"Connection failed: {str(e)}")
        overall_status = "degraded"

    # --- OpenSearch check ---
    try:
        if opensearch_client.health_check():
            stats = opensearch_client.get_index_stats()
            doc_count = stats.get("document_count", 0)
            index_name = stats.get("index_name", "unknown")
            services["opensearch"] = ServiceStatus(
                status="healthy",
                message=f"Index '{index_name}' with {doc_count} documents",
            )
        else:
            services["opensearch"] = ServiceStatus(status="unhealthy", message="Cluster not responding")
            overall_status = "degraded"
    except Exception as e:
        services["opensearch"] = ServiceStatus(status="unhealthy", message=str(e))
        overall_status = "degraded"

    # --- Ollama check ---
    try:
        ollama_client = OllamaClient(settings)
        ollama_health = await ollama_client.health_check()
        services["ollama"] = ServiceStatus(status=ollama_health["status"], message=ollama_health["message"])
        if ollama_health["status"] != "healthy":
            overall_status = "degraded"
    except OllamaConnectionError as e:
        services["ollama"] = ServiceStatus(status="unhealthy", message=f"Cannot connect to Ollama: {str(e)}")
        overall_status = "degraded"
    except OllamaTimeoutError as e:
        services["ollama"] = ServiceStatus(status="unhealthy", message=f"Ollama timeout: {str(e)}")
        overall_status = "degraded"
    except OllamaException as e:
        services["ollama"] = ServiceStatus(status="unhealthy", message=f"Ollama error: {str(e)}")
        overall_status = "degraded"
    except Exception as e:
        services["ollama"] = ServiceStatus(status="unhealthy", message=f"Unexpected Ollama error: {str(e)}")
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        service_name=settings.service_name,
        services=services,
    )
