# API Reference - aerodb-py

Complete API documentation for the AeroDB Python SDK.

## Table of Contents

- [AeroDBClient](#aerodbclient)
- [Authentication](#authentication)
- [Database](#database)
- [Real-time](#real-time)
- [Storage](#storage)
- [Functions](#functions)
- [Types](#types)

---

## AeroDBClient

Main entry point for the SDK.

### Constructor

```python
AeroDBClient(
    url: str,
    key: Optional[str] = None,
    schema: str = "public",
    headers: Optional[Dict[str, str]] = None,
    realtime_url: Optional[str] = None
)
```

**Parameters:**
- `url` (str, required): Base API URL
- `key` (str, optional): API key (not required if using email/password auth)
- `schema` (str, optional): Database schema (default: 'public')
- `headers` (dict, optional): Custom HTTP headers
- `realtime_url` (str, optional): Override WebSocket URL

**Example:**
```python
client = AeroDBClient(
    url="https://api.aerodb.com",
    key="aero_abc123..."
)
```

### Context Manager

Always use as async context manager:

```python
async with AeroDBClient(url="...", key="...") as client:
    # Use client here
    pass
# Automatic cleanup
```

### Properties

- `auth: AuthClient` - Authentication methods
- `storage: StorageClient` - File upload/download
- `functions: FunctionsClient` - Serverless functions

### Methods

#### `from_(table: str) -> QueryBuilder`

Create a query builder for a table.

```python
result = await client.from_("users").select("*").execute()
```

#### `channel(name: str) -> RealtimeChannel`

Create a real-time channel subscription.

```python
channel = client.channel("posts")
await channel.on("INSERT", handler).subscribe()
```

---

## Authentication

### `auth.sign_up(email, password)`

Create a new user account.

```python
result = await client.auth.sign_up(
    email="user@example.com",
    password="password123"
)
```

**Returns:** `AeroDBResponse[AuthData]`

**Types:**
```python
@dataclass
class AuthData:
    user: User
    session: Session
```

### `auth.sign_in(email, password)`

Sign in an existing user.

```python
result = await client.auth.sign_in(
    email="user@example.com",
    password="password123"
)
```

**Returns:** `AeroDBResponse[AuthData]`

### `auth.sign_out()`

Sign out the current user.

```python
await client.auth.sign_out()
```

**Returns:** `AeroDBResponse[None]`

### `auth.get_user()`

Get the currently signed-in user.

```python
result = await client.auth.get_user()
user = result.data
```

**Returns:** `AeroDBResponse[User]`

### `auth.refresh_session()`

Refresh the current session.

```python
result = await client.auth.refresh_session()
```

**Returns:** `AeroDBResponse[Session]`

---

## Database

### Query Builder Methods

All methods return `self` for chaining except `execute()`.

#### `select(columns: str = "*") -> QueryBuilder`

Specify columns to return.

```python
.select("id, name, email")
.select("*")
.select("id, author:users(name)")  # Join
```

#### `eq(column: str, value: Any) -> QueryBuilder`

Filter where column equals value.

```python
.eq("status", "active")
.eq("age", 25)
```

#### `neq(column, value) -> QueryBuilder`

Filter where column does not equal value.

```python
.neq("role", "guest")
```

#### `gt(column, value)` / `gte(column, value)`

Greater than / greater than or equal.

```python
.gt("age", 18)
.gte("score", 100)
```

#### `lt(column, value)` / `lte(column, value)`

Less than / less than or equal.

```python
.lt("price", 100)
.lte("quantity", 10)
```

#### `like(column, pattern)` / `ilike(column, pattern)`

Pattern matching (case-sensitive / case-insensitive).

```python
.like("name", "%John%")
.ilike("email", "%@gmail.com")
```

#### `in_(column, values)`

Filter where column is in list.

```python
.in_("status", ["active", "pending", "archived"])
```

#### `order(column, ascending=True)`

Sort results.

```python
.order("created_at", ascending=False)
.order("name")  # ascending by default
```

#### `limit(count: int)`

Limit number of results.

```python
.limit(10)
```

#### `offset(count: int)`

Skip a number of results.

```python
.offset(20)
```

#### `insert(data: Union[Dict, List[Dict]])`

Insert one or more rows.

```python
await client.from_("users").insert({"name": "John"})
await client.from_("users").insert([{"name": "Jane"}, {"name": "Bob"}])
```

**Returns:** `AeroDBResponse[List[Dict]]`

#### `update(data: Dict)`

Update matching rows.

```python
await client.from_("users").eq("id", "123").update({"name": "Jane"})
```

**Returns:** `AeroDBResponse[List[Dict]]`

#### `delete()`

Delete matching rows.

```python
await client.from_("users").eq("id", "123").delete()
```

**Returns:** `AeroDBResponse[None]`

#### `execute()`

Execute the query.

```python
result = await query.execute()
data = result.data  # List[Dict] | None
error = result.error  # AeroDBError | None
```

**Returns:** `AeroDBResponse[List[Dict]]`

---

## Real-time

### `channel(name: str) -> RealtimeChannel`

Create a new channel subscription.

```python
channel = client.channel("posts")
```

### `RealtimeChannel.on(event, callback)`

Register event handler.

```python
async def on_insert(payload):
    print(f"New row: {payload.new}")

async def on_update(payload):
    print(f"Updated: {payload.new}")
    print(f"Old: {payload.old}")

await channel.on("INSERT", on_insert).on("UPDATE", on_update)
```

**Events:** `"INSERT"` | `"UPDATE"` | `"DELETE"`

**Payload:**
```python
@dataclass
class RealtimePayload:
    type: str  # "INSERT" | "UPDATE" | "DELETE"
    table: str
    new: Optional[Dict[str, Any]]
    old: Optional[Dict[str, Any]]
```

### `RealtimeChannel.subscribe()`

Start listening for events.

```python
await channel.subscribe()
```

### `RealtimeChannel.unsubscribe()`

Stop listening and close connection.

```python
await channel.unsubscribe()
```

---

## Storage

### `storage.from_(bucket: str) -> StorageBucket`

Select a storage bucket.

```python
bucket = client.storage.from_("avatars")
```

### `StorageBucket.upload(path, file_bytes)`

Upload a file.

```python
with open("avatar.png", "rb") as f:
    file_bytes = f.read()
    result = await bucket.upload("user-123/avatar.png", file_bytes)
```

**Returns:** `AeroDBResponse[Dict]`

**Response:** `{"path": str, "url": str}`

### `StorageBucket.download(path)`

Download a file.

```python
result = await bucket.download("user-123/avatar.png")
file_bytes = result.data
```

**Returns:** `AeroDBResponse[bytes]`

### `StorageBucket.get_public_url(path)`

Get public URL for a file.

```python
url = bucket.get_public_url("user-123/avatar.png")
```

**Returns:** `str`

### `StorageBucket.remove(paths)`

Delete one or more files.

```python
await bucket.remove("user-123/avatar.png")
await bucket.remove(["file1.png", "file2.png"])
```

**Returns:** `AeroDBResponse[None]`

### `StorageBucket.list(path="", limit=100, offset=0)`

List files in a path.

```python
result = await bucket.list("users/", limit=100)
files = result.data
```

**Returns:** `AeroDBResponse[List[FileObject]]`

---

## Functions

### `functions.invoke(name, body=None, headers=None)`

Invoke a serverless function.

```python
result = await client.functions.invoke(
    "send-email",
    body={"to": "user@example.com", "subject": "Hello"}
)
```

**Parameters:**
- `name` (str): Function name
- `body` (any, optional): Request body
- `headers` (dict, optional): Custom headers

**Returns:** `AeroDBResponse[Any]`

---

## Types

### `AeroDBResponse[T]`

```python
@dataclass
class AeroDBResponse(Generic[T]):
    data: Optional[T]
    error: Optional[AeroDBError]
```

### `AeroDBError`

```python
@dataclass
class AeroDBError:
    message: str
    status: Optional[int] = None
    code: Optional[str] = None
```

### `User`

```python
@dataclass
class User:
    id: str
    email: str
    created_at: str
    updated_at: str
```

### `Session`

```python
@dataclass
class Session:
    access_token: str
    refresh_token: str
    expires_at: int
    user: User
```

### `FileObject`

```python
@dataclass
class FileObject:
    name: str
    id: str
    size: int
    created_at: str
    updated_at: str
    last_accessed_at: str
    metadata: Dict[str, Any]
```

## Type Hints Usage

```python
from aerodb import AeroDBClient, AeroDBResponse, User
from typing import List

async def get_admins(client: AeroDBClient) -> AeroDBResponse[List[User]]:
    return await (
        client.from_("users")
        .select("*")
        .eq("role", "admin")
        .execute()
    )
```
