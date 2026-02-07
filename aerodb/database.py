"""
Database module - QueryBuilder and PostgrestClient for AeroDB.

Implements fluent API for building database queries.
Query is not executed until execute() is called.
"""

from typing import TypeVar, Generic, Optional, List, Dict, Any, Union
import aiohttp

from .types import AeroDBResponse, AeroDBError

T = TypeVar("T")


class QueryBuilder(Generic[T]):
    """Fluent API for building database queries."""

    def __init__(
        self,
        collection: str,
        base_url: str,
        session: aiohttp.ClientSession,
        api_key: Optional[str],
        get_token: Any,  # Callable that returns Optional[str]
        schema: str = "public",
    ) -> None:
        self._collection = collection
        self._base_url = base_url
        self._session = session
        self._api_key = api_key
        self._get_token = get_token
        self._schema = schema

        self._select_fields: str = "*"
        self._filters: List[Dict[str, Any]] = []
        self._order_fields: List[Dict[str, Any]] = []
        self._limit_value: Optional[int] = None
        self._offset_value: Optional[int] = None

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["apikey"] = self._api_key
        token = self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if self._schema != "public":
            headers["Accept-Profile"] = self._schema
        return headers

    def select(self, fields: str = "*") -> "QueryBuilder[T]":
        """Select specific columns."""
        self._select_fields = fields
        return self

    def eq(self, field: str, value: Any) -> "QueryBuilder[T]":
        """Filter: equal."""
        self._filters.append({"field": field, "op": "eq", "value": value})
        return self

    def neq(self, field: str, value: Any) -> "QueryBuilder[T]":
        """Filter: not equal."""
        self._filters.append({"field": field, "op": "neq", "value": value})
        return self

    def gt(self, field: str, value: Any) -> "QueryBuilder[T]":
        """Filter: greater than."""
        self._filters.append({"field": field, "op": "gt", "value": value})
        return self

    def gte(self, field: str, value: Any) -> "QueryBuilder[T]":
        """Filter: greater than or equal."""
        self._filters.append({"field": field, "op": "gte", "value": value})
        return self

    def lt(self, field: str, value: Any) -> "QueryBuilder[T]":
        """Filter: less than."""
        self._filters.append({"field": field, "op": "lt", "value": value})
        return self

    def lte(self, field: str, value: Any) -> "QueryBuilder[T]":
        """Filter: less than or equal."""
        self._filters.append({"field": field, "op": "lte", "value": value})
        return self

    def like(self, field: str, pattern: str) -> "QueryBuilder[T]":
        """Filter: LIKE pattern match (case sensitive)."""
        self._filters.append({"field": field, "op": "like", "value": pattern})
        return self

    def ilike(self, field: str, pattern: str) -> "QueryBuilder[T]":
        """Filter: ILIKE pattern match (case insensitive)."""
        self._filters.append({"field": field, "op": "ilike", "value": pattern})
        return self

    def in_(self, field: str, values: List[Any]) -> "QueryBuilder[T]":
        """Filter: IN array of values."""
        self._filters.append({"field": field, "op": "in", "value": values})
        return self

    def order(
        self, field: str, ascending: bool = True, nulls_first: Optional[bool] = None
    ) -> "QueryBuilder[T]":
        """Order results."""
        self._order_fields.append({
            "field": field,
            "ascending": ascending,
            "nulls_first": nulls_first,
        })
        return self

    def limit(self, count: int) -> "QueryBuilder[T]":
        """Limit number of results."""
        self._limit_value = count
        return self

    def offset(self, count: int) -> "QueryBuilder[T]":
        """Offset for pagination."""
        self._offset_value = count
        return self

    def _build_query_string(self) -> str:
        """Build the query string for GET requests."""
        params: List[str] = []

        # Select
        if self._select_fields:
            params.append(f"select={self._select_fields}")

        # Filters
        for f in self._filters:
            value = self._format_filter_value(f["op"], f["value"])
            params.append(f"{f['field']}={f['op']}.{value}")

        # Order
        if self._order_fields:
            order_parts = []
            for o in self._order_fields:
                part = f"{o['field']}.{'asc' if o['ascending'] else 'desc'}"
                if o["nulls_first"] is not None:
                    part += f".{'nullsfirst' if o['nulls_first'] else 'nullslast'}"
                order_parts.append(part)
            params.append(f"order={','.join(order_parts)}")

        # Pagination
        if self._limit_value is not None:
            params.append(f"limit={self._limit_value}")
        if self._offset_value is not None:
            params.append(f"offset={self._offset_value}")

        return "&".join(params)

    def _format_filter_value(self, op: str, value: Any) -> str:
        """Format filter value based on operator."""
        if op == "in" and isinstance(value, list):
            return f"({','.join(str(v) for v in value)})"
        if value is None:
            return "null"
        return str(value)

    async def execute(self) -> AeroDBResponse[List[T]]:
        """Execute SELECT query."""
        try:
            query_string = self._build_query_string()
            url = f"{self._base_url}/rest/v1/{self._collection}?{query_string}"

            async with self._session.get(url, headers=self._get_headers()) as response:
                data = await response.json()

                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=data.get("error", "Query failed"),
                            status=response.status,
                        ),
                    )

                return AeroDBResponse(data=data, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def insert(
        self, data: Union[Dict[str, Any], List[Dict[str, Any]]]
    ) -> AeroDBResponse[List[T]]:
        """Insert rows."""
        try:
            url = f"{self._base_url}/rest/v1/{self._collection}"
            headers = self._get_headers()
            headers["Prefer"] = "return=representation"

            async with self._session.post(
                url, json=data, headers=headers
            ) as response:
                result = await response.json()

                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=result.get("error", "Insert failed"),
                            status=response.status,
                        ),
                    )

                return AeroDBResponse(data=result, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def update(self, data: Dict[str, Any]) -> AeroDBResponse[List[T]]:
        """Update rows matching filters."""
        try:
            query_string = self._build_query_string()
            url = f"{self._base_url}/rest/v1/{self._collection}?{query_string}"
            headers = self._get_headers()
            headers["Prefer"] = "return=representation"

            async with self._session.patch(
                url, json=data, headers=headers
            ) as response:
                result = await response.json()

                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=result.get("error", "Update failed"),
                            status=response.status,
                        ),
                    )

                return AeroDBResponse(data=result, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def delete(self) -> AeroDBResponse[List[T]]:
        """Delete rows matching filters."""
        try:
            query_string = self._build_query_string()
            url = f"{self._base_url}/rest/v1/{self._collection}?{query_string}"
            headers = self._get_headers()
            headers["Prefer"] = "return=representation"

            async with self._session.delete(url, headers=headers) as response:
                result = await response.json()

                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=result.get("error", "Delete failed"),
                            status=response.status,
                        ),
                    )

                return AeroDBResponse(data=result, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )


class PostgrestClient:
    """Database operations wrapper. Creates QueryBuilder instances."""

    def __init__(
        self,
        base_url: str,
        session: aiohttp.ClientSession,
        api_key: Optional[str],
        get_token: Any,
        schema: str = "public",
    ) -> None:
        self._base_url = base_url
        self._session = session
        self._api_key = api_key
        self._get_token = get_token
        self._schema = schema

    def from_(self, collection: str) -> QueryBuilder[Dict[str, Any]]:
        """Create a query builder for a collection.
        Uses from_ to avoid Python keyword clash."""
        return QueryBuilder(
            collection=collection,
            base_url=self._base_url,
            session=self._session,
            api_key=self._api_key,
            get_token=self._get_token,
            schema=self._schema,
        )
