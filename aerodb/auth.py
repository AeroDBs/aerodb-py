"""
AuthClient - Authentication operations for AeroDB.

Handles user signup, signin, signout, and token refresh.
Uses Result pattern - never raises exceptions.
"""

from typing import Optional, Dict, Any, Callable, Awaitable
import aiohttp

from .types import (
    AeroDBResponse,
    AeroDBError,
    User,
    Session,
    AuthData,
)


class AuthClient:
    """Authentication client for user management."""

    def __init__(
        self,
        base_url: str,
        session: aiohttp.ClientSession,
        api_key: Optional[str] = None,
    ) -> None:
        self._auth_url = f"{base_url}/auth"
        self._session = session
        self._api_key = api_key
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["apikey"] = self._api_key
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def get_token(self) -> Optional[str]:
        """Get current access token."""
        return self._access_token

    def get_session(self) -> Optional[Session]:
        """Get current session."""
        if self._access_token and self._refresh_token:
            return Session(
                access_token=self._access_token,
                refresh_token=self._refresh_token,
            )
        return None

    async def sign_up(
        self,
        email: str,
        password: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AeroDBResponse[AuthData]:
        """Sign up a new user."""
        try:
            payload: Dict[str, Any] = {"email": email, "password": password}
            if metadata:
                payload["metadata"] = metadata

            async with self._session.post(
                f"{self._auth_url}/signup",
                json=payload,
                headers=self._get_headers(),
            ) as response:
                data = await response.json()

                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=data.get("error", "Signup failed"),
                            status=response.status,
                            code=data.get("code"),
                        ),
                    )

                # Store tokens
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")

                user = User(
                    id=data["user"]["id"],
                    email=data["user"]["email"],
                    email_verified=data["user"].get("email_verified", False),
                    created_at=data["user"]["created_at"],
                    metadata=data["user"].get("metadata"),
                )
                session = Session(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    expires_in=data.get("expires_in"),
                )

                return AeroDBResponse(
                    data=AuthData(user=user, session=session),
                    error=None,
                )
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def sign_in(
        self,
        email: str,
        password: str,
    ) -> AeroDBResponse[AuthData]:
        """Sign in with email and password."""
        try:
            async with self._session.post(
                f"{self._auth_url}/login",
                json={"email": email, "password": password},
                headers=self._get_headers(),
            ) as response:
                data = await response.json()

                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=data.get("error", "Login failed"),
                            status=response.status,
                            code=data.get("code"),
                        ),
                    )

                # Store tokens
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")

                user = User(
                    id=data["user"]["id"],
                    email=data["user"]["email"],
                    email_verified=data["user"].get("email_verified", False),
                    created_at=data["user"]["created_at"],
                    metadata=data["user"].get("metadata"),
                )
                session = Session(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    expires_in=data.get("expires_in"),
                )

                return AeroDBResponse(
                    data=AuthData(user=user, session=session),
                    error=None,
                )
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def sign_out(self) -> AeroDBResponse[None]:
        """Sign out the current user."""
        try:
            if self._refresh_token:
                async with self._session.post(
                    f"{self._auth_url}/logout",
                    json={"refresh_token": self._refresh_token},
                    headers=self._get_headers(),
                ) as response:
                    pass  # Ignore response

            # Clear tokens
            self._access_token = None
            self._refresh_token = None

            return AeroDBResponse(data=None, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def get_user(self) -> AeroDBResponse[User]:
        """Get the current authenticated user."""
        if not self._access_token:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message="Not authenticated", code="NOT_AUTHENTICATED"),
            )

        try:
            async with self._session.get(
                f"{self._auth_url}/user",
                headers=self._get_headers(),
            ) as response:
                data = await response.json()

                if not response.ok:
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=data.get("error", "Failed to fetch user"),
                            status=response.status,
                        ),
                    )

                user = User(
                    id=data["id"],
                    email=data["email"],
                    email_verified=data.get("email_verified", False),
                    created_at=data["created_at"],
                    metadata=data.get("metadata"),
                )
                return AeroDBResponse(data=user, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )

    async def refresh_session(self) -> AeroDBResponse[Session]:
        """Refresh the access token."""
        if not self._refresh_token:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message="No refresh token", code="NO_REFRESH_TOKEN"),
            )

        try:
            async with self._session.post(
                f"{self._auth_url}/refresh",
                json={"refresh_token": self._refresh_token},
                headers=self._get_headers(),
            ) as response:
                data = await response.json()

                if not response.ok:
                    self._access_token = None
                    self._refresh_token = None
                    return AeroDBResponse(
                        data=None,
                        error=AeroDBError(
                            message=data.get("error", "Refresh failed"),
                            status=response.status,
                        ),
                    )

                # Store new tokens
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")

                session = Session(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    expires_in=data.get("expires_in"),
                )
                return AeroDBResponse(data=session, error=None)
        except Exception as e:
            return AeroDBResponse(
                data=None,
                error=AeroDBError(message=str(e), code="NETWORK_ERROR"),
            )
