# aerodb-py

Official Python SDK for AeroDB.

## Installation

```bash
pip install aerodb-py
# or
poetry add aerodb-py
```

## Quick Start

```python
import asyncio
from aerodb import AeroDBClient

async def main():
    async with AeroDBClient(url="https://your-project.aerodb.com", key="your-api-key") as client:
        # Authentication
        result = await client.auth.sign_in(email="user@example.com", password="password123")
        if result.error:
            print(f"Error: {result.error.message}")
            return

        # Database queries
        result = await client.from_("users").select("*").eq("role", "admin").limit(10).execute()
        print(result.data)

        # Insert data
        await client.from_("posts").insert({"title": "Hello World", "content": "My first post"})

        # Real-time subscriptions
        async def on_insert(payload):
            print(f"New message: {payload.new}")

        channel = client.channel("messages")
        await channel.on("INSERT", on_insert).subscribe()

asyncio.run(main())
```

## API Reference

### AeroDBClient

Main entry point. Creates authenticated connections to AeroDB.

```python
client = AeroDBClient(
    url="https://api.aerodb.com",  # Required
    key="your-api-key",             # Optional if using sign_in
    schema="public",                # Default: 'public'
    headers={"X-Custom": "value"},  # Optional custom headers
)
```

### Authentication

```python
# Sign up
result = await client.auth.sign_up(email="user@example.com", password="password123")

# Sign in
result = await client.auth.sign_in(email="user@example.com", password="password123")

# Sign out
await client.auth.sign_out()

# Get current user
result = await client.auth.get_user()

# Refresh session
result = await client.auth.refresh_session()
```

### Database

```python
# Select with filters
result = await (
    client.from_("users")
    .select("id, name, email")
    .eq("role", "admin")
    .gt("age", 18)
    .order("created_at", ascending=False)
    .limit(10)
    .execute()
)

# Insert
await client.from_("users").insert({"name": "John"})

# Update
await client.from_("users").eq("id", "123").update({"name": "Jane"})

# Delete
await client.from_("users").eq("id", "123").delete()
```

**Available filters:** `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `like`, `ilike`, `in_`

### Real-time

```python
async def on_insert(payload):
    print(f"New: {payload.new}")

async def on_update(payload):
    print(f"Updated: {payload.new}")

channel = client.channel("posts")
await channel.on("INSERT", on_insert).on("UPDATE", on_update).subscribe()

# Unsubscribe
await channel.unsubscribe()
```

### Storage

```python
# Upload
result = await client.storage.from_("bucket").upload("path/file.png", file_bytes)

# Download
result = await client.storage.from_("bucket").download("path/file.png")

# Delete
await client.storage.from_("bucket").remove(["path/file.png"])

# List
result = await client.storage.from_("bucket").list_("path/")
```

### Functions

```python
result = await client.functions.invoke("my-function", body={"foo": "bar"})
```

## Error Handling

All methods return `AeroDBResponse` with `data` and `error` - no exceptions raised.

```python
result = await client.from_("users").execute()

if result.error:
    print(f"Error: {result.error.message}")
else:
    print(result.data)
```

## Type Hints

Full type hints for mypy strict mode:

```python
from aerodb import AeroDBClient, AeroDBResponse, User

async def get_user(client: AeroDBClient) -> AeroDBResponse[User]:
    return await client.auth.get_user()
```

## License

MIT
