"""
AuthClient unit tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiohttp import ClientResponse, ClientSession

from aerodb.auth import AuthClient


class MockResponse:
    """Mock aiohttp response."""

    def __init__(self, data: dict, status: int = 200) -> None:
        self._data = data
        self.status = status
        self.ok = status < 400

    async def json(self) -> dict:
        return self._data

    async def __aenter__(self) -> "MockResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.fixture
def mock_session() -> MagicMock:
    """Create mock aiohttp session."""
    return MagicMock(spec=ClientSession)


@pytest.fixture
def auth_client(mock_session: MagicMock) -> AuthClient:
    """Create AuthClient with mock session."""
    return AuthClient("https://api.test.com", mock_session, "test-api-key")


@pytest.mark.asyncio
async def test_sign_up_success(auth_client: AuthClient, mock_session: MagicMock) -> None:
    """Test successful sign up."""
    mock_session.post.return_value = MockResponse({
        "user": {
            "id": "123",
            "email": "test@example.com",
            "email_verified": False,
            "created_at": "2024-01-01T00:00:00Z",
        },
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
    })

    result = await auth_client.sign_up("test@example.com", "password123")

    assert result.error is None
    assert result.data is not None
    assert result.data.user.email == "test@example.com"
    assert result.data.session.access_token == "access-token"


@pytest.mark.asyncio
async def test_sign_up_failure(auth_client: AuthClient, mock_session: MagicMock) -> None:
    """Test sign up failure."""
    mock_session.post.return_value = MockResponse(
        {"error": "Email already exists"},
        status=409,
    )

    result = await auth_client.sign_up("existing@example.com", "password123")

    assert result.data is None
    assert result.error is not None
    assert result.error.message == "Email already exists"


@pytest.mark.asyncio
async def test_sign_in_success(auth_client: AuthClient, mock_session: MagicMock) -> None:
    """Test successful sign in."""
    mock_session.post.return_value = MockResponse({
        "user": {
            "id": "123",
            "email": "test@example.com",
            "email_verified": True,
            "created_at": "2024-01-01T00:00:00Z",
        },
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
    })

    result = await auth_client.sign_in("test@example.com", "password123")

    assert result.error is None
    assert result.data is not None
    assert result.data.user.id == "123"


@pytest.mark.asyncio
async def test_sign_in_invalid_credentials(auth_client: AuthClient, mock_session: MagicMock) -> None:
    """Test sign in with invalid credentials."""
    mock_session.post.return_value = MockResponse(
        {"error": "Invalid credentials"},
        status=401,
    )

    result = await auth_client.sign_in("test@example.com", "wrong-password")

    assert result.data is None
    assert result.error is not None
    assert result.error.status == 401


@pytest.mark.asyncio
async def test_get_user_unauthenticated(auth_client: AuthClient) -> None:
    """Test get user when not authenticated."""
    result = await auth_client.get_user()

    assert result.data is None
    assert result.error is not None
    assert result.error.code == "NOT_AUTHENTICATED"


@pytest.mark.asyncio
async def test_refresh_session_no_token(auth_client: AuthClient) -> None:
    """Test refresh session without refresh token."""
    result = await auth_client.refresh_session()

    assert result.data is None
    assert result.error is not None
    assert result.error.code == "NO_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_sign_out(auth_client: AuthClient, mock_session: MagicMock) -> None:
    """Test sign out."""
    mock_session.post.return_value = MockResponse({})

    # Simulate being signed in
    auth_client._access_token = "token"
    auth_client._refresh_token = "refresh"

    result = await auth_client.sign_out()

    assert result.error is None
    assert auth_client._access_token is None
    assert auth_client._refresh_token is None
