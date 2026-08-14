import os
import httpx
import logging
from typing import Optional

from .models import SourceMappingRequest, SourceMappingResult
from .exceptions import (
    SourceIntelligenceConnectionError,
    SourceIntelligenceTimeoutError,
    SourceIntelligenceAPIError,
    SourceIntelligenceMalformedResponseError,
)

logger = logging.getLogger("codeloom.source_intelligence.client")


class SourceIntelligenceClient:
    """Client for communicating with the Node.js Source Intelligence Microservice."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        # Allow override via environment or config
        self.base_url = base_url or os.environ.get("SOURCE_INTELLIGENCE_URL", "http://localhost:8001")
        self.timeout = timeout

    async def map_source(self, request: SourceMappingRequest) -> SourceMappingResult:
        """
        Sends a SourceMappingRequest to the Node.js service and returns a SourceMappingResult.
        """
        endpoint = f"{self.base_url.rstrip('/')}/v1/source-mappings"
        logger.info(f"Source intelligence request started for finding: {request.runtimeEvidence.ruleId}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=request.model_dump())

            response.raise_for_status()

            # Deserialize
            result_data = response.json()
            result = SourceMappingResult.model_validate(result_data)
            
            logger.info(f"Source intelligence request completed. Status: {result.status}")
            return result

        except httpx.TimeoutException as e:
            logger.error(f"Source intelligence request timed out after {self.timeout}s")
            raise SourceIntelligenceTimeoutError(f"Request to {endpoint} timed out.") from e

        except httpx.ConnectError as e:
            logger.error(f"Source intelligence connection failed: {e}")
            raise SourceIntelligenceConnectionError(f"Failed to connect to {endpoint}") from e

        except httpx.HTTPStatusError as e:
            logger.error(f"Source intelligence HTTP error: {e.response.status_code}")
            raise SourceIntelligenceAPIError(
                f"HTTP {e.response.status_code} from Source Intelligence: {e.response.text}",
                status_code=e.response.status_code,
                response_body=e.response.text,
            ) from e
            
        except Exception as e:
            # Handle unparseable JSON or other unexpected errors
            if isinstance(e, SourceIntelligenceAPIError):
                raise
            logger.error(f"Source intelligence malformed response or unknown error: {e}")
            raise SourceIntelligenceMalformedResponseError(f"Failed to parse response: {e}") from e
