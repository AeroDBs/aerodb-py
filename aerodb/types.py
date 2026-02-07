"""
Type definitions for AeroDB Python SDK.
All types are fully annotated for mypy strict mode.
"""

from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Dict, Any, List
from datetime import datetime

T = TypeVar("T")


@dataclass
class AeroDBError:
    """Standard error type for all AeroDB operations."""
    message: str
    status: Optional[int] = None
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class AeroDBResponse(Generic[T]):
    """Standard response type for all AeroDB async operations.
    Uses Result pattern - never raises exceptions."""
    data: Optional[T]
    error: Optional[AeroDBError]


@dataclass
class User:
    """User type returned from auth operations."""
    id: str
    email: str
    email_verified: bool
    created_at: str
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Session:
    """Session type containing authentication tokens."""
    access_token: str
    refresh_token: str
    expires_at: Optional[int] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = None


@dataclass
class AuthData:
    """Combined auth response with user and session."""
    user: User
    session: Session


@dataclass
class FileObject:
    """File object returned from storage operations."""
    id: str
    name: str
    bucket: str
    path: str
    size: int
    content_type: str
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RealtimePayload:
    """Payload received from realtime events."""
    type: str  # 'INSERT', 'UPDATE', 'DELETE'
    table: str
    schema: str
    commit_timestamp: str
    new: Optional[Dict[str, Any]]
    old: Optional[Dict[str, Any]]


# Type aliases for common response types
AuthResponse = AeroDBResponse[AuthData]
UserResponse = AeroDBResponse[User]
SessionResponse = AeroDBResponse[Session]
FileResponse = AeroDBResponse[FileObject]
ListResponse = AeroDBResponse[List[Dict[str, Any]]]
