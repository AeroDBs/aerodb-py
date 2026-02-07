"""
AeroDB Python Client SDK

Production-ready async client library for AeroDB.
Provides type-safe access to Auth, Database, Realtime, Storage, and Functions APIs.

Example usage:
    from aerodb import AeroDBClient

    client = AeroDBClient(url="https://api.aerodb.com", key="your-api-key")

    # Auth
    result = await client.auth.sign_in(email="user@example.com", password="password123")

    # Database queries
    result = await client.from_("users").select("*").eq("role", "admin").limit(10).execute()

    # Realtime subscriptions
    channel = client.channel("messages")
    await channel.on("INSERT", lambda payload: print(payload)).subscribe()
"""

from .client import AeroDBClient
from .types import (
    AeroDBResponse,
    AeroDBError,
    User,
    Session,
    FileObject,
)

__version__ = "1.0.0"

__all__ = [
    "AeroDBClient",
    "AeroDBResponse",
    "AeroDBError",
    "User",
    "Session",
    "FileObject",
]
