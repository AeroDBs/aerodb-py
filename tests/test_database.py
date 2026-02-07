"""
QueryBuilder unit tests.
"""

import pytest
from unittest.mock import MagicMock
from aiohttp import ClientSession

from aerodb.database import QueryBuilder


class MockResponse:
    """Mock aiohttp response."""

    def __init__(self, data: object, status: int = 200) -> None:
        self._data = data
        self.status = status
        self.ok = status < 400

    async def json(self) -> object:
        return self._data

    async def __aenter__(self) -> "MockResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.fixture
def mock_session() -> MagicMock:
    """Create mock aiohttp session."""
    return MagicMock(spec=ClientSession)


def get_token() -> str:
    return "test-token"


@pytest.fixture
def query_builder(mock_session: MagicMock) -> QueryBuilder[dict]:
    """Create QueryBuilder with mock session."""
    return QueryBuilder(
        "users",
        "https://api.test.com",
        mock_session,
        "test-api-key",
        get_token,
    )


@pytest.mark.asyncio
async def test_select(query_builder: QueryBuilder[dict], mock_session: MagicMock) -> None:
    """Test select query."""
    mock_session.get.return_value = MockResponse([{"id": "1", "name": "Test"}])

    result = await query_builder.select("id, name").execute()

    assert result.error is None
    assert result.data is not None
    assert len(result.data) == 1

    # Verify URL contains select
    call_args = mock_session.get.call_args
    assert "select=id, name" in call_args[0][0]


@pytest.mark.asyncio
async def test_eq_filter(query_builder: QueryBuilder[dict], mock_session: MagicMock) -> None:
    """Test eq filter."""
    mock_session.get.return_value = MockResponse([])

    await query_builder.eq("role", "admin").execute()

    call_args = mock_session.get.call_args
    assert "role=eq.admin" in call_args[0][0]


@pytest.mark.asyncio
async def test_gt_filter(query_builder: QueryBuilder[dict], mock_session: MagicMock) -> None:
    """Test gt filter."""
    mock_session.get.return_value = MockResponse([])

    await query_builder.gt("age", 18).execute()

    call_args = mock_session.get.call_args
    assert "age=gt.18" in call_args[0][0]


@pytest.mark.asyncio
async def test_order(query_builder: QueryBuilder[dict], mock_session: MagicMock) -> None:
    """Test order."""
    mock_session.get.return_value = MockResponse([])

    await query_builder.order("created_at", ascending=False).execute()

    call_args = mock_session.get.call_args
    assert "order=created_at.desc" in call_args[0][0]


@pytest.mark.asyncio
async def test_limit_offset(query_builder: QueryBuilder[dict], mock_session: MagicMock) -> None:
    """Test limit and offset."""
    mock_session.get.return_value = MockResponse([])

    await query_builder.limit(10).offset(20).execute()

    call_args = mock_session.get.call_args
    assert "limit=10" in call_args[0][0]
    assert "offset=20" in call_args[0][0]


@pytest.mark.asyncio
async def test_insert(query_builder: QueryBuilder[dict], mock_session: MagicMock) -> None:
    """Test insert."""
    mock_session.post.return_value = MockResponse([{"id": "1", "name": "John"}])

    result = await query_builder.insert({"name": "John"})

    assert result.error is None
    mock_session.post.assert_called_once()


@pytest.mark.asyncio
async def test_update(query_builder: QueryBuilder[dict], mock_session: MagicMock) -> None:
    """Test update."""
    mock_session.patch.return_value = MockResponse([{"id": "1", "name": "Jane"}])

    result = await query_builder.eq("id", "1").update({"name": "Jane"})

    assert result.error is None
    mock_session.patch.assert_called_once()


@pytest.mark.asyncio
async def test_delete(query_builder: QueryBuilder[dict], mock_session: MagicMock) -> None:
    """Test delete."""
    mock_session.delete.return_value = MockResponse([{"id": "1"}])

    result = await query_builder.eq("id", "1").delete()

    assert result.error is None
    mock_session.delete.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling(query_builder: QueryBuilder[dict], mock_session: MagicMock) -> None:
    """Test error handling."""
    mock_session.get.return_value = MockResponse(
        {"error": "Table not found"},
        status=404,
    )

    result = await query_builder.execute()

    assert result.data is None
    assert result.error is not None
    assert result.error.status == 404
