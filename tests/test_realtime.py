"""
RealtimeClient unit tests.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json

from aerodb.realtime import RealtimeClient, RealtimeChannel
from aerodb.types import RealtimePayload


@pytest.fixture
def realtime_client() -> RealtimeClient:
    """Create RealtimeClient."""
    return RealtimeClient(
        "wss://api.test.com/realtime/v1/websocket",
        "test-api-key",
        lambda: "test-token",
    )


class TestRealtimeClient:
    """Tests for RealtimeClient."""

    def test_channel_creation(self, realtime_client: RealtimeClient) -> None:
        """Test creating a channel."""
        channel = realtime_client.channel("test-channel")

        assert isinstance(channel, RealtimeChannel)
        assert channel._name == "test-channel"

    def test_channel_reuse(self, realtime_client: RealtimeClient) -> None:
        """Test that same channel is returned for same name."""
        channel1 = realtime_client.channel("my-channel")
        channel2 = realtime_client.channel("my-channel")

        assert channel1 is channel2

    def test_different_channels(self, realtime_client: RealtimeClient) -> None:
        """Test that different channels are created for different names."""
        channel1 = realtime_client.channel("channel-1")
        channel2 = realtime_client.channel("channel-2")

        assert channel1 is not channel2
        assert channel1._name == "channel-1"
        assert channel2._name == "channel-2"


class TestRealtimeChannel:
    """Tests for RealtimeChannel."""

    @pytest.fixture
    def channel(self, realtime_client: RealtimeClient) -> RealtimeChannel:
        """Create a test channel."""
        return realtime_client.channel("test-messages")

    def test_on_handler_registration(self, channel: RealtimeChannel) -> None:
        """Test registering event handlers."""
        handler = MagicMock()

        result = channel.on("INSERT", handler)

        # Should return self for chaining
        assert result is channel
        assert "INSERT" in channel._handlers
        assert handler in channel._handlers["INSERT"]

    def test_multiple_handlers_same_event(self, channel: RealtimeChannel) -> None:
        """Test registering multiple handlers for same event."""
        handler1 = MagicMock()
        handler2 = MagicMock()

        channel.on("UPDATE", handler1)
        channel.on("UPDATE", handler2)

        assert len(channel._handlers["UPDATE"]) == 2

    def test_handler_chaining(self, channel: RealtimeChannel) -> None:
        """Test handler registration chaining."""
        handler1 = MagicMock()
        handler2 = MagicMock()
        handler3 = MagicMock()

        result = (
            channel
            .on("INSERT", handler1)
            .on("UPDATE", handler2)
            .on("DELETE", handler3)
        )

        assert result is channel
        assert "INSERT" in channel._handlers
        assert "UPDATE" in channel._handlers
        assert "DELETE" in channel._handlers

    def test_off_removes_handler(self, channel: RealtimeChannel) -> None:
        """Test removing a specific handler."""
        handler = MagicMock()
        channel.on("INSERT", handler)
        assert handler in channel._handlers["INSERT"]

        channel.off("INSERT", handler)
        assert handler not in channel._handlers.get("INSERT", [])

    def test_off_nonexistent_handler(self, channel: RealtimeChannel) -> None:
        """Test removing non-existent handler doesn't error."""
        handler = MagicMock()
        # Should not raise
        channel.off("INSERT", handler)

    @pytest.mark.asyncio
    async def test_handle_message_calls_handlers(self, channel: RealtimeChannel) -> None:
        """Test that message handling calls registered handlers."""
        handler = AsyncMock()
        channel.on("INSERT", handler)

        payload = RealtimePayload(
            type="INSERT",
            table="users",
            schema="public",
            commit_timestamp="2024-01-01T00:00:00Z",
            new={"id": 1, "name": "Test"},
            old=None,
        )
        await channel.dispatch(payload)

        handler.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_handle_message_multiple_handlers(self, channel: RealtimeChannel) -> None:
        """Test that all handlers are called for an event."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        channel.on("UPDATE", handler1)
        channel.on("UPDATE", handler2)

        payload = RealtimePayload(
            type="UPDATE",
            table="users",
            schema="public",
            commit_timestamp="2024-01-01T00:00:00Z",
            new={"id": 1},
            old={"id": 1},
        )
        await channel.dispatch(payload)

        handler1.assert_awaited_once()
        handler2.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_message_async_handler(self, channel: RealtimeChannel) -> None:
        """Test that async handlers are awaited."""
        async_handler = AsyncMock()
        channel.on("DELETE", async_handler)

        payload = RealtimePayload(
            type="DELETE",
            table="users",
            schema="public",
            commit_timestamp="2024-01-01T00:00:00Z",
            new=None,
            old={"id": 1},
        )
        await channel.dispatch(payload)

        async_handler.assert_awaited_once_with(payload)

    @pytest.mark.asyncio
    async def test_handle_message_no_matching_handlers(self, channel: RealtimeChannel) -> None:
        """Test message with no handlers doesn't error."""
        payload = RealtimePayload(
            type="UNKNOWN_EVENT",
            table="",
            schema="",
            commit_timestamp="",
            new=None,
            old=None,
        )
        # Should not raise
        await channel.dispatch(payload)

    def test_channel_state_initial(self, channel: RealtimeChannel) -> None:
        """Test initial channel state."""
        assert channel._subscribed is False

    @pytest.mark.asyncio
    async def test_unsubscribe_clears_handlers(self, channel: RealtimeChannel) -> None:
        """Test that unsubscribe clears state."""
        handler = MagicMock()
        channel.on("INSERT", handler)
        channel._subscribed = True
        # Mock the _send_message to avoid real WebSocket calls
        channel._send_message = AsyncMock()

        await channel.unsubscribe()

        assert channel._subscribed is False
