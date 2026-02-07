"""
StorageClient unit tests.
"""

import pytest
from unittest.mock import MagicMock
from aiohttp import ClientSession

from aerodb.storage import StorageClient, BucketOperations


class MockResponse:
    """Mock aiohttp response."""

    def __init__(self, data: dict | bytes | list, status: int = 200) -> None:
        self._data = data
        self.status = status
        self.ok = status < 400

    async def json(self) -> dict | list:
        if isinstance(self._data, (dict, list)):
            return self._data
        return {}

    async def read(self) -> bytes:
        if isinstance(self._data, bytes):
            return self._data
        return b""

    async def __aenter__(self) -> "MockResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


@pytest.fixture
def mock_session() -> MagicMock:
    """Create mock aiohttp session."""
    return MagicMock(spec=ClientSession)


@pytest.fixture
def storage_client(mock_session: MagicMock) -> StorageClient:
    """Create StorageClient with mock session."""
    return StorageClient(
        "https://api.test.com",
        mock_session,
        "test-api-key",
        lambda: "test-token",
    )


class TestBucketOperations:
    """Tests for bucket-specific operations."""

    @pytest.mark.asyncio
    async def test_upload_success(
        self, storage_client: StorageClient, mock_session: MagicMock
    ) -> None:
        """Test successful file upload."""
        mock_session.post.return_value = MockResponse({
            "id": "file-123",
            "name": "test.txt",
            "created_at": "2024-01-01T00:00:00Z",
        })

        bucket = storage_client.from_("avatars")
        result = await bucket.upload("user/avatar.png", b"image data", "image/png")

        assert result.error is None
        assert result.data is not None
        assert result.data.name == "test.txt"
        assert result.data.bucket == "avatars"

    @pytest.mark.asyncio
    async def test_upload_failure(
        self, storage_client: StorageClient, mock_session: MagicMock
    ) -> None:
        """Test upload failure."""
        mock_session.post.return_value = MockResponse(
            {"error": "Bucket not found"},
            status=404,
        )

        bucket = storage_client.from_("nonexistent")
        result = await bucket.upload("file.txt", b"data")

        assert result.data is None
        assert result.error is not None
        assert result.error.status == 404

    @pytest.mark.asyncio
    async def test_upload_with_upsert(
        self, storage_client: StorageClient, mock_session: MagicMock
    ) -> None:
        """Test upload with upsert option."""
        mock_session.post.return_value = MockResponse({
            "id": "file-123",
            "name": "test.txt",
        })

        bucket = storage_client.from_("docs")
        await bucket.upload("file.txt", b"data", upsert=True)

        # Verify upsert header was sent
        call_args = mock_session.post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert headers.get("x-upsert") == "true"

    @pytest.mark.asyncio
    async def test_download_success(
        self, storage_client: StorageClient, mock_session: MagicMock
    ) -> None:
        """Test successful file download."""
        file_content = b"downloaded file content"
        mock_session.get.return_value = MockResponse(file_content)

        bucket = storage_client.from_("files")
        result = await bucket.download("document.pdf")

        assert result.error is None
        assert result.data == file_content

    @pytest.mark.asyncio
    async def test_download_not_found(
        self, storage_client: StorageClient, mock_session: MagicMock
    ) -> None:
        """Test download file not found."""
        mock_session.get.return_value = MockResponse({}, status=404)

        bucket = storage_client.from_("files")
        result = await bucket.download("missing.pdf")

        assert result.data is None
        assert result.error is not None
        assert result.error.status == 404

    @pytest.mark.asyncio
    async def test_remove_success(
        self, storage_client: StorageClient, mock_session: MagicMock
    ) -> None:
        """Test successful file removal."""
        mock_session.delete.return_value = MockResponse({})

        bucket = storage_client.from_("files")
        result = await bucket.remove(["file1.txt", "file2.txt"])

        assert result.error is None

    @pytest.mark.asyncio
    async def test_list_files(
        self, storage_client: StorageClient, mock_session: MagicMock
    ) -> None:
        """Test listing files."""
        mock_session.get.return_value = MockResponse([
            {"name": "file1.txt", "size": 100},
            {"name": "file2.txt", "size": 200},
        ])

        bucket = storage_client.from_("docs")
        result = await bucket.list_()

        assert result.error is None
        assert result.data is not None
        assert len(result.data) == 2

    @pytest.mark.asyncio
    async def test_list_with_prefix(
        self, storage_client: StorageClient, mock_session: MagicMock
    ) -> None:
        """Test listing files with prefix filter."""
        mock_session.get.return_value = MockResponse([])

        bucket = storage_client.from_("docs")
        await bucket.list_(path="folder/", limit=10, offset=0)

        call_args = mock_session.get.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert "prefix=folder/" in url
        assert "limit=10" in url

    def test_get_public_url(self, storage_client: StorageClient) -> None:
        """Test public URL generation."""
        bucket = storage_client.from_("public-bucket")
        url = bucket.get_public_url("images/photo.jpg")

        assert url == "https://api.test.com/storage/v1/object/public/public-bucket/images/photo.jpg"
