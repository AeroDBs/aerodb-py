"""
FunctionsClient unit tests.
"""

import pytest
from unittest.mock import MagicMock
from aiohttp import ClientSession

from aerodb.functions import FunctionsClient


class MockResponse:
    """Mock aiohttp response."""

    def __init__(
        self,
        data: dict | str,
        status: int = 200,
        content_type: str = "application/json",
    ) -> None:
        self._data = data
        self.status = status
        self.ok = status < 400
        self.content_type = content_type

    async def json(self) -> dict:
        if isinstance(self._data, dict):
            return self._data
        return {}

    async def text(self) -> str:
        if isinstance(self._data, str):
            return self._data
        return str(self._data)

    async def __aenter__(self) -> "MockResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.fixture
def mock_session() -> MagicMock:
    """Create mock aiohttp session."""
    return MagicMock(spec=ClientSession)


@pytest.fixture
def functions_client(mock_session: MagicMock) -> FunctionsClient:
    """Create FunctionsClient with mock session."""
    return FunctionsClient(
        "https://api.test.com",
        mock_session,
        "test-api-key",
        lambda: "test-token",
    )


class TestFunctionsClient:
    """Tests for function invocation."""

    @pytest.mark.asyncio
    async def test_invoke_post_success(
        self, functions_client: FunctionsClient, mock_session: MagicMock
    ) -> None:
        """Test successful POST function invocation."""
        mock_session.post.return_value = MockResponse({
            "result": "success",
            "data": {"greeting": "Hello, World!"},
        })

        result = await functions_client.invoke("hello-world")

        assert result.error is None
        assert result.data is not None
        assert result.data["result"] == "success"

    @pytest.mark.asyncio
    async def test_invoke_with_body(
        self, functions_client: FunctionsClient, mock_session: MagicMock
    ) -> None:
        """Test function invocation with request body."""
        mock_session.post.return_value = MockResponse({
            "greeting": "Hello, Alice!",
        })

        result = await functions_client.invoke(
            "greet",
            body={"name": "Alice"},
        )

        assert result.error is None
        assert result.data["greeting"] == "Hello, Alice!"

        # Verify body was passed
        call_args = mock_session.post.call_args
        assert call_args.kwargs.get("json") == {"name": "Alice"}

    @pytest.mark.asyncio
    async def test_invoke_get_method(
        self, functions_client: FunctionsClient, mock_session: MagicMock
    ) -> None:
        """Test GET function invocation."""
        mock_session.get.return_value = MockResponse({
            "items": [1, 2, 3],
        })

        result = await functions_client.invoke("get-items", method="GET")

        assert result.error is None
        assert result.data["items"] == [1, 2, 3]
        mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_with_custom_headers(
        self, functions_client: FunctionsClient, mock_session: MagicMock
    ) -> None:
        """Test function invocation with custom headers."""
        mock_session.post.return_value = MockResponse({})

        await functions_client.invoke(
            "auth-function",
            headers={"X-Custom-Header": "custom-value"},
        )

        call_args = mock_session.post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert headers.get("X-Custom-Header") == "custom-value"

    @pytest.mark.asyncio
    async def test_invoke_function_not_found(
        self, functions_client: FunctionsClient, mock_session: MagicMock
    ) -> None:
        """Test invocation of non-existent function."""
        mock_session.post.return_value = MockResponse(
            {"error": "Function not found"},
            status=404,
        )

        result = await functions_client.invoke("nonexistent")

        assert result.data is None
        assert result.error is not None
        assert result.error.status == 404

    @pytest.mark.asyncio
    async def test_invoke_function_error(
        self, functions_client: FunctionsClient, mock_session: MagicMock
    ) -> None:
        """Test function execution error."""
        mock_session.post.return_value = MockResponse(
            {"error": "Internal function error"},
            status=500,
        )

        result = await functions_client.invoke("failing-function")

        assert result.data is None
        assert result.error is not None
        assert result.error.status == 500

    @pytest.mark.asyncio
    async def test_invoke_text_response(
        self, functions_client: FunctionsClient, mock_session: MagicMock
    ) -> None:
        """Test function returning text instead of JSON."""
        mock_session.post.return_value = MockResponse(
            "Plain text response",
            content_type="text/plain",
        )

        result = await functions_client.invoke("text-function")

        assert result.error is None
        assert result.data == "Plain text response"

    @pytest.mark.asyncio
    async def test_invoke_timeout_error(
        self, functions_client: FunctionsClient, mock_session: MagicMock
    ) -> None:
        """Test function timeout."""
        mock_session.post.return_value = MockResponse(
            {"error": "Function timed out"},
            status=504,
        )

        result = await functions_client.invoke("slow-function")

        assert result.error is not None
        assert result.error.status == 504
