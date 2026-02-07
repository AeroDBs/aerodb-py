# Getting Started with aerodb-py

The official Python SDK for AeroDB - a strict, deterministic, self-hostable database with BaaS capabilities.

## Prerequisites

- Python 3.8+
- pip or poetry
- An AeroDB instance (self-hosted or managed)

## Installation

```bash
pip install aerodb-py
# or
poetry add aerodb-py
```

## Quick Start

### 1. Initialize the Client

```python
import asyncio
from aerodb import AeroDBClient

async def main():
    async with AeroDBClient(
        url="https://your-project.aerodb.com",
        key="your-api-key",  # Optional if using email/password auth
    ) as client:
        # Your code here
        pass

asyncio.run(main())
```

### 2. Authenticate

```python
# Sign up new user
result = await client.auth.sign_up(
    email="user@example.com",
    password="securepassword123"
)

if result.error:
    print(f"Error: {result.error.message}")
else:
    print(f"User created: {result.data.user.email}")

# Or sign in existing user
result = await client.auth.sign_in(
    email="user@example.com",
    password="securepassword123"
)
```

### 3. Query Data

```python
# Fetch all users
result = await client.from_("users").select("*").execute()
users = result.data

# Fetch with filters
result = await (
    client.from_("users")
    .select("id, name, email")
    .eq("role", "admin")
    .order("created_at", ascending=False)
    .limit(10)
    .execute()
)
admins = result.data
print(f"Found {len(admins)} admin users")
```

### 4. Insert & Update Data

```python
# Insert
result = await client.from_("posts").insert({
    "title": "Hello World",
    "content": "My first AeroDB post",
    "author_id": "user-123"
})
new_post = result.data

# Update
await (
    client.from_("posts")
    .eq("id", new_post["id"])
    .update({"published": True})
)

# Delete
await (
    client.from_("posts")
    .eq("id", new_post["id"])
    .delete()
)
```

### 5. Real-time Subscriptions

```python
async def on_insert(payload):
    print(f"New post: {payload.new}")

async def on_update(payload):
    print(f"Post updated: {payload.new}")

# Subscribe to changes
channel = client.channel("posts")
await channel.on("INSERT", on_insert).on("UPDATE", on_update).subscribe()

# Keep connection alive
await asyncio.sleep(60)

# Cleanup
await channel.unsubscribe()
```

### 6. File Storage

```python
# Upload file
with open("avatar.png", "rb") as f:
    file_bytes = f.read()
    
result = await (
    client.storage
    .from_("avatars")
    .upload(f"users/{user_id}/avatar.png", file_bytes)
)

# Get public URL
url = (
    client.storage
    .from_("avatars")
    .get_public_url(f"users/{user_id}/avatar.png")
)

# Download file
result = await (
    client.storage
    .from_("avatars")
    .download(f"users/{user_id}/avatar.png")
)
file_bytes = result.data
```

### 7. Serverless Functions

```python
result = await client.functions.invoke(
    "send-email",
    body={
        "to": "user@example.com",
        "subject": "Welcome!",
        "text": "Thanks for signing up"
    }
)
```

## Type Hints Support

Full type hints for mypy strict mode:

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

# result.data is List[User] | None, fully typed!
```

## Error Handling

All methods return `AeroDBResponse` with `data` and `error`:

```python
result = await client.from_("users").select("*").execute()

if result.error:
    # Handle error - no exception raised
    print(f"Error {result.error.status}: {result.error.message}")
    return

# Safely use data
for user in result.data:
    print(user["name"])
```

## Common Patterns

### Paginated Lists

```python
page = 1
per_page = 20

result = await (
    client.from_("users")
    .select("*")
    .order("created_at", ascending=False)
    .offset((page - 1) * per_page)
    .limit(per_page)
    .execute()
)
```

### Search

```python
result = await (
    client.from_("posts")
    .select("*")
    .ilike("title", "%search term%")
    .execute()
)
```

### Joins (via nested selects)

```python
result = await (
    client.from_("posts")
    .select("*, author:users(id, name)")
    .execute()
)

# Returns: [{"id": 1, "title": "...", "author": {"id": "...", "name": "..."}}, ...]
```

### Context Manager Pattern

Always use async context manager for automatic cleanup:

```python
async with AeroDBClient(url="...", key="...") as client:
    # All operations here
    result = await client.from_("users").select("*").execute()
# Automatic cleanup on exit
```

### Batch Operations

```python
# Insert multiple rows
posts = [
    {"title": "Post 1", "content": "..."},
    {"title": "Post 2", "content": "..."},
    {"title": "Post 3", "content": "..."},
]

result = await client.from_("posts").insert(posts)
print(f"Inserted {len(result.data)} posts")
```

## Configuration

```python
client = AeroDBClient(
    url="https://api.aerodb.com",      # Required
    key="your-api-key",                 # Optional
    schema="public",                    # Default schema
    headers={"X-Custom": "value"},      # Custom headers
    realtime_url="wss://realtime.aerodb.com"  # Override realtime URL
)
```

## Available Query Filters

| Method | Description | Example |
|--------|-------------|---------|
| `eq(field, value)` | Equals | `.eq("status", "active")` |
| `neq(field, value)` | Not equals | `.neq("role", "guest")` |
| `gt(field, value)` | Greater than | `.gt("age", 18)` |
| `gte(field, value)` | Greater than or equal | `.gte("score", 100)` |
| `lt(field, value)` | Less than | `.lt("price", 50)` |
| `lte(field, value)` | Less than or equal | `.lte("quantity", 10)` |
| `like(field, pattern)` | Pattern match (case-sensitive) | `.like("name", "%john%")` |
| `ilike(field, pattern)` | Pattern match (case-insensitive) | `.ilike("email", "%@gmail.com")` |
| `in_(field, values)` | In list | `.in_("status", ["active", "pending"])` |

## Next Steps

- [Architecture](./ARCHITECTURE.md) - Learn how the SDK is structured
- [API Reference](./API_REFERENCE.md) - Complete API documentation
- [Authentication Guide](./AUTHENTICATION.md) - Auth flows and best practices
- [Database Guide](./DATABASE.md) - Advanced querying
- [Real-time Guide](./REALTIME.md) - WebSocket subscriptions
- [Storage Guide](./STORAGE.md) - File uploads and management
- [Best Practices](./BEST_PRACTICES.md) - Patterns and anti-patterns
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues

## Community & Support

- **GitHub**: [aerodb/aerodb-py](https://github.com/aerodb/aerodb-py)
- **Discord**: [Join our community](https://discord.gg/aerodb)
- **Documentation**: [docs.aerodb.com](https://docs.aerodb.com)
- **Issues**: [Report bugs](https://github.com/aerodb/aerodb-py/issues)

## License

MIT - See [LICENSE](../LICENSE) for details
