"""
AeroDBClient - Main client class for AeroDB Python SDK.

Entry point for all AeroDB operations.
Initializes and exposes auth, database, realtime, storage, and functions clients.
"""

from typing import Optional, Dict, Any
import aiohttp
from urllib.parse import urlparse

from .auth import AuthClient
from .database import PostgrestClient, QueryBuilder
from .storage import StorageClient
from .functions import FunctionsClient
from .realtime import RealtimeClient, RealtimeChannel


class AeroDBClient:
    """
    Main AeroDB client class.

    Example:
        async with AeroDBClient(url="https://api.aerodb.com", key="your-key") as client:
            result = await client.auth.sign_in(email="user@example.com", password="password")
    """

    def __init__(
        self,
        url: str,
        key: Optional[str] = None,
        schema: str = "public",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize AeroDB client.

        Args:
            url: Base URL of the AeroDB instance
            key: API key for authentication (optional if using sign_in)
            schema: Database schema to use (default: 'public')
            headers: Custom headers to include in all requests
        """
        if not url:
            raise ValueError("AeroDBClient: url is required")

        # Normalize URL
        self._base_url = url.rstrip("/")
        self._api_key = key
        self._schema = schema
        self._custom_headers = headers or {}

        # Create HTTP session
        self._session = aiohttp.ClientSession(headers=self._custom_headers)

        # Initialize auth client
        self.auth = AuthClient(self._base_url, self._session, self._api_key)

        # Initialize database client
        self._db = PostgrestClient(
            self._base_url,
            self._session,
            self._api_key,
            self.auth.get_token,
            self._schema,
        )

        # Initialize storage client
        self.storage = StorageClient(
            self._base_url,
            self._session,
            self._api_key,
            self.auth.get_token,
        )

        # Initialize functions client
        self.functions = FunctionsClient(
            self._base_url,
            self._session,
            self._api_key,
            self.auth.get_token,
        )

        # Initialize realtime client
        ws_url = self._build_websocket_url()
        self.realtime = RealtimeClient(ws_url, self._api_key, self.auth.get_token)

    def _build_websocket_url(self) -> str:
        """Build WebSocket URL from base URL."""
        parsed = urlparse(self._base_url)
        protocol = "wss" if parsed.scheme == "https" else "ws"
        return f"{protocol}://{parsed.netloc}/realtime/v1/websocket"

    def from_(self, collection: str) -> QueryBuilder[Dict[str, Any]]:
        """
        Create a query builder for a database collection/table.
        Uses from_ to avoid Python keyword clash.
        """
        return self._db.from_(collection)

    def channel(self, name: str) -> RealtimeChannel:
        """Create or get a realtime channel."""
        return self.realtime.channel(name)

    async def close(self) -> None:
        """Close the client and release resources."""
        await self.realtime.disconnect()
        await self._session.close()

    async def __aenter__(self) -> "AeroDBClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.close()
