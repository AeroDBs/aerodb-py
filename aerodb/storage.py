"""
StorageClient - File storage operations for AeroDB.

Upload, download, delete, and list files in storage buckets.
"""

from typing import Optional, List, Dict, Any
import aiohttp

from .types import AeroDBResponse, AeroDBError, FileObject


class BucketOperations:
    """Bucket-specific file operations."""

    def __init__(
        self,
        bucket_name: str,
        storage_url: str,
        session: aiohttp.ClientSession,
        api_key: Optional[str],
        get_token: Any,
    ) -> None:
        self._bucket_name = bucket_name
        self._storage_url = storage_url
        self._session = session
        self._api_key = api_key
        self._get_token = get_token

    def _get_headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        """Build request headers."""
        headers: Dict[str, str] = {}
        if content_type:
            headers["Content-Type"] = content_type
        if self._api_key:
            headers["apikey"] = self._api_key
        token = self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def upload(
        self,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        upsert: bool = False,
    ) -> AeroDBResponse[FileObject]:
        """Upload a file to the bucket."""
        try:
            url = f"{self._storage_url}/object/{self._bucket_name}/{path}"
            headers = self._get_headers(content_type)
            if upsert:
                headers["x-upsert"] = "true"

            async with self._session.post(
                url, data=data, headers=headers
            ) as response:
                result = await response.json()

                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=result.get("error", "Upload failed"),
                            status=response.status,
                        ),
                    )

                file_obj = FileObject(
                    id=result.get("id", ""),
                    name=result.get("name", path),
                    bucket=self._bucket_name,
                    path=path,
                    size=len(data),
                    content_type=content_type,
                    created_at=result.get("created_at", ""),
                    updated_at=result.get("updated_at", ""),
                )
                return AeroDBResponse(data=file_obj, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def download(self, path: str) -> AeroDBResponse[bytes]:
        """Download a file from the bucket."""
        try:
            url = f"{self._storage_url}/object/{self._bucket_name}/{path}"

            async with self._session.get(
                url, headers=self._get_headers()
            ) as response:
                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message="Download failed",
                            status=response.status,
                        ),
                    )

                data = await response.read()
                return AeroDBResponse(data=data, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def remove(self, paths: List[str]) -> AeroDBResponse[None]:
        """Delete files from the bucket."""
        try:
            url = f"{self._storage_url}/object/{self._bucket_name}"
            headers = self._get_headers("application/json")

            async with self._session.delete(
                url, json={"prefixes": paths}, headers=headers
            ) as response:
                if not response.ok:
                    result = await response.json()
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=result.get("error", "Delete failed"),
                            status=response.status,
                        ),
                    )

                return AeroDBResponse(data=None, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def list_(
        self,
        path: str = "",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> AeroDBResponse[List[Dict[str, Any]]]:
        """List files in the bucket."""
        try:
            params: List[str] = []
            if path:
                params.append(f"prefix={path}")
            if limit is not None:
                params.append(f"limit={limit}")
            if offset is not None:
                params.append(f"offset={offset}")

            query = "&".join(params)
            url = f"{self._storage_url}/object/list/{self._bucket_name}"
            if query:
                url += f"?{query}"

            async with self._session.get(
                url, headers=self._get_headers()
            ) as response:
                result = await response.json()

                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=result.get("error", "List failed"),
                            status=response.status,
                        ),
                    )

                return AeroDBResponse(data=result, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    def get_public_url(self, path: str) -> str:
        """Get public URL for a file (if bucket is public)."""
        return f"{self._storage_url}/object/public/{self._bucket_name}/{path}"


class StorageClient:
    """Storage client for file operations."""

    def __init__(
        self,
        base_url: str,
        session: aiohttp.ClientSession,
        api_key: Optional[str],
        get_token: Any,
    ) -> None:
        self._storage_url = f"{base_url}/storage/v1"
        self._session = session
        self._api_key = api_key
        self._get_token = get_token

    def from_(self, bucket: str) -> BucketOperations:
        """Get bucket operations for a specific bucket."""
        return BucketOperations(
            bucket_name=bucket,
            storage_url=self._storage_url,
            session=self._session,
            api_key=self._api_key,
            get_token=self._get_token,
        )
