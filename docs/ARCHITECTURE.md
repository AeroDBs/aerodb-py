# aerodb-py Architecture

## Package Overview

The AeroDB Python SDK is an async-first client library that provides a unified interface to all AeroDB services: authentication, database queries, real-time subscriptions, file storage, and serverless functions.

## Design Principles

1. **Async/Await First** - All I/O operations are async
2. **No Exceptions** - All methods return `AeroDBResponse` with `data` and `error`
3. **Type Safety** - Full type hints for mypy strict mode
4. **Fluent API** - Method chaining for query building
5. **Context Managers** - Automatic resource cleanup

## Package Structure

```
aerodb/
├── __init__.py              # Main exports
├── client.py                # AeroDBClient class
├── auth.py                  # AuthClient
├── database.py              # QueryBuilder, DatabaseClient
├── realtime.py              # RealtimeClient, RealtimeChannel
├── storage.py               # StorageClient, StorageBucket
├── functions.py             # FunctionsClient
└── types.py                 # Shared types
```

## Core Classes

### AeroDBClient

Entry point that composes all sub-clients:

```python
class AeroDBClient:
    def __init__(
        self,
        url: str,
        key: Optional[str] = None,
        schema: str = "public",
        headers: Optional[Dict[str, str]] = None,
        realtime_url: Optional[str] = None
    ):
        self.auth = AuthClient(self)
        self._db = DatabaseClient(self)
        self.storage = StorageClient(self)
        self.functions = FunctionsClient(self)
        self._realtime = RealtimeClient(self)
    
    def from_(self, table: str) -> QueryBuilder:
        """Convenience method for database queries"""
        return self._db.from_(table)
    
    def channel(self, name: str) -> RealtimeChannel:
        """Convenience method for realtime subscriptions"""
        return self._realtime.channel(name)
    
    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, *args):
        """Context manager exit - cleanup resources"""
        await self._realtime.disconnect()
```

### QueryBuilder

Fluent API for building PostgREST-compatible queries:

```python
await (
    client.from_("users")
    .select("id, name, email")
    .eq("role", "admin")
    .gt("age", 18)
    .order("created_at", ascending=False)
    .limit(10)
    .execute()
)
```

**Operators supported**: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `like`, `ilike`, `in_`

### RealtimeChannel

WebSocket-based pub/sub using `websockets` library:

```python
channel = client.channel("posts")
await channel.on("INSERT", handler).on("UPDATE", handler).subscribe()
```

## Type System

```python
from typing import Generic, TypeVar, Optional
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class AeroDBResponse(Generic[T]):
    """Response envelope for all operations"""
    data: Optional[T]
    error: Optional[AeroDBError]

@dataclass
class AeroDBError:
    """Standardized error format"""
    message: str
    status: Optional[int] = None
    code: Optional[str] = None
```

## HTTP Communication

All HTTP requests use `aiohttp`:

- **Method**: Based on operation (GET, POST, PATCH, DELETE)
- **Headers**: `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Base URL**: `{url}/rest/v1/{table}` for database
- **Query Params**: Filters converted to PostgREST format

Example: `.eq("role", "admin")` → `?role=eq.admin`

## WebSocket Protocol

Real-time uses `websockets` library connecting to `{realtime_url or url}/realtime`:

```python
# Subscribe
await ws.send(json.dumps({"type": "subscribe", "channel": "posts"}))

# Event received
{
    "type": "event",
    "channel": "posts",
    "payload": {
        "type": "INSERT",
        "new": {"id": 1, "title": "Hello"}
    }
}

# Unsubscribe
await ws.send(json.dumps({"type": "unsubscribe", "channel": "posts"}))
```

## Authentication Flow

1. User calls `await client.auth.sign_in(email, password)`
2. SDK sends POST to `/auth/login`
3. Response contains `access_token` and `refresh_token`
4. Tokens stored in instance variable
5. All subsequent requests include `Authorization: Bearer <access_token>`
6. SDK auto-refreshes on 401 responses

## Module Boundaries

| Module | Responsibility | Dependencies |
|--------|---------------|--------------|
| `client.py` | Entry point, composes sub-clients | All modules |
| `auth.py` | Sign up, sign in, session management | `aiohttp` |
| `database.py` | Query builder + REST API wrapper | `aiohttp` |
| `realtime.py` | WebSocket connection + channels | `websockets`, `asyncio` |
| `storage.py` | File upload/download | `aiohttp`, `FormData` |
| `functions.py` | Edge function invocation | `aiohttp` |
| `types.py` | Shared types and dataclasses | `dataclasses`, `typing` |

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.8"
aiohttp = "^3.9.0"
websockets = "^12.0"
```

## Testing Strategy

- **Unit Tests**: pytest + pytest-asyncio
- **Integration Tests**: Against local AeroDB instance
- **Type Tests**: mypy strict mode
- **E2E Tests**: Real-world scenarios in examples/

## Error Handling Pattern

All methods follow the same pattern:

```python
async def some_operation(self) -> AeroDBResponse[SomeType]:
    try:
        async with self.session.get(url) as response:
            if response.status >= 400:
                error_data = await response.json()
                return AeroDBResponse(
                    data=None,
                    error=AeroDBError(
                        message=error_data.get("error", "Unknown error"),
                        status=response.status
                    )
                )
            
            data = await response.json()
            return AeroDBResponse(data=data, error=None)
    
    except Exception as e:
        return AeroDBResponse(
            data=None,
            error=AeroDBError(message=str(e))
        )
```

## Resource Management

Uses async context managers for automatic cleanup:

```python
async with AeroDBClient(url="...", key="...") as client:
    # All operations
    result = await client.from_("users").select("*").execute()
# WebSocket connections automatically closed
# HTTP sessions automatically closed
```

## Performance Considerations

1. **Connection Pooling**: aiohttp reuses HTTP connections
2. **Lazy Initialization**: WebSocket only connects when first subscription is made
3. **Query Batching**: Not implemented (future consideration)
4. **Async Context**: All I/O is non-blocking

## Security

- **HTTPS Only**: Enforced in production
- **Token Storage**: In-memory only (not persisted to disk)
- **No Eval**: No dynamic code execution
- **Input Validation**: All user inputs are validated

## Future Enhancements

- [ ] Sync client wrapper for non-async code
- [ ] Retry with exponential backoff
- [ ] Query result streaming for large datasets
- [ ] Connection health monitoring
- [ ] Offline support with local cache
