"""
FunctionsClient - Serverless function invocation for AeroDB.

Invoke edge functions deployed to AeroDB.
"""

from typing import TypeVar, Optional, Dict, Any
import aiohttp

from .types import AeroDBResponse, AeroDBError

T = TypeVar("T")


class FunctionsClient:
    """Functions client for serverless invocation."""

    def __init__(
        self,
        base_url: str,
        session: aiohttp.ClientSession,
        api_key: Optional[str],
        get_token: Any,
    ) -> None:
        self._functions_url = f"{base_url}/functions/v1"
        self._session = session
        self._api_key = api_key
        self._get_token = get_token

    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """Build request headers."""
        headers: Dict[str, str] = {"Content-Type": content_type}
        if self._api_key:
            headers["apikey"] = self._api_key
        token = self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def invoke(
        self,
        function_name: str,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "POST",
    ) -> AeroDBResponse[Any]:
        """Invoke a function by name."""
        try:
            url = f"{self._functions_url}/{function_name}"
            request_headers = self._get_headers()
            if headers:
                request_headers.update(headers)

            if method.upper() == "GET":
                async with self._session.get(
                    url, headers=request_headers
                ) as response:
                    if response.content_type == "application/json":
                        result = await response.json()
                    else:
                        result = await response.text()

                    if not response.ok:
                        return AeroDBResponse(
                            data=None,
                            error=AeroDBError(
                                message=str(result) if isinstance(result, str) else result.get("error", "Invoke failed"),
                                status=response.status,
                            ),
                        )

                    return AeroDBResponse(data=result, error=None)
            else:
                async with self._session.post(
                    url, json=body, headers=request_headers
                ) as response:
                    if response.content_type == "application/json":
                        result = await response.json()
                    else:
                        result = await response.text()

                    if not response.ok:
                        return AeroDBResponse(
                            data=None,
                            error=AeroDBError(
                                message=str(result) if isinstance(result, str) else result.get("error", "Invoke failed"),
                                status=response.status,
                            ),
                        )

                    return AeroDBResponse(data=result, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )
