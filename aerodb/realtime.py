"""
RealtimeClient - WebSocket connection manager for AeroDB.

Manages WebSocket connection lifecycle with auto-reconnection.
"""

from typing import Optional, Dict, Any, Callable, List, Awaitable
import asyncio
import json
import aiohttp

from .types import RealtimePayload


# Type alias for event handlers
EventHandler = Callable[[RealtimePayload], Awaitable[None]]


class RealtimeChannel:
    """Subscription management for a single channel."""

    def __init__(
        self,
        name: str,
        send_message: Callable[[Dict[str, Any]], Awaitable[None]],
        on_subscribe: Callable[["RealtimeChannel"], None],
        on_unsubscribe: Callable[["RealtimeChannel"], None],
    ) -> None:
        self._name = name
        self._send_message = send_message
        self._on_subscribe = on_subscribe
        self._on_unsubscribe = on_unsubscribe
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._subscribed = False

    @property
    def name(self) -> str:
        """Get channel name."""
        return self._name

    @property
    def subscribed(self) -> bool:
        """Check if subscribed."""
        return self._subscribed

    def on(
        self, event: str, callback: EventHandler
    ) -> "RealtimeChannel":
        """Register an event handler."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(callback)
        return self

    def off(
        self, event: str, callback: Optional[EventHandler] = None
    ) -> "RealtimeChannel":
        """Remove an event handler."""
        if event in self._handlers:
            if callback is None:
                del self._handlers[event]
            else:
                self._handlers[event] = [
                    h for h in self._handlers[event] if h != callback
                ]
        return self

    async def subscribe(self) -> "RealtimeChannel":
        """Subscribe to the channel."""
        if self._subscribed:
            return self

        await self._send_message({
            "type": "subscribe",
            "channel": self._name,
        })

        self._subscribed = True
        self._on_subscribe(self)
        return self

    async def unsubscribe(self) -> None:
        """Unsubscribe from the channel."""
        if not self._subscribed:
            return

        await self._send_message({
            "type": "unsubscribe",
            "channel": self._name,
        })

        self._subscribed = False
        self._handlers.clear()
        self._on_unsubscribe(self)

    async def dispatch(self, payload: RealtimePayload) -> None:
        """Dispatch an event to handlers."""
        event_type = payload.type

        # Call specific event handlers
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    await handler(payload)
                except Exception:
                    pass  # Ignore handler errors

        # Call wildcard handlers
        if "*" in self._handlers:
            for handler in self._handlers["*"]:
                try:
                    await handler(payload)
                except Exception:
                    pass


class RealtimeClient:
    """WebSocket connection manager for realtime subscriptions."""

    def __init__(
        self,
        ws_url: str,
        api_key: Optional[str],
        get_token: Any,
    ) -> None:
        self._ws_url = ws_url
        self._api_key = api_key
        self._get_token = get_token
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._channels: Dict[str, RealtimeChannel] = {}
        self._connected = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._receive_task: Optional[asyncio.Task[None]] = None

    def channel(self, name: str) -> RealtimeChannel:
        """Create or get a channel."""
        if name in self._channels:
            return self._channels[name]

        channel = RealtimeChannel(
            name=name,
            send_message=self._send_message,
            on_subscribe=self._handle_subscribe,
            on_unsubscribe=self._handle_unsubscribe,
        )
        self._channels[name] = channel
        return channel

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        if self._connected:
            return

        # Build URL with auth params
        url = self._ws_url
        params: List[str] = []
        if self._api_key:
            params.append(f"apikey={self._api_key}")
        token = self._get_token()
        if token:
            params.append(f"token={token}")
        if params:
            url += ("&" if "?" in url else "?") + "&".join(params)

        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(url)
        self._connected = True

        # Start receive loop
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        self._connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

        if self._session:
            await self._session.close()
            self._session = None

        self._channels.clear()

    async def _receive_loop(self) -> None:
        """Receive and dispatch messages."""
        if not self._ws:
            return

        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    if data.get("type") == "event" and "channel" in data:
                        channel_name = data["channel"]
                        channel = self._channels.get(channel_name)
                        if channel and "payload" in data:
                            payload_data = data["payload"]
                            payload = RealtimePayload(
                                type=payload_data.get("type", ""),
                                table=payload_data.get("table", ""),
                                schema=payload_data.get("schema", ""),
                                commit_timestamp=payload_data.get("commit_timestamp", ""),
                                new=payload_data.get("new"),
                                old=payload_data.get("old"),
                            )
                            await channel.dispatch(payload)
                except Exception:
                    pass  # Ignore parse errors
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                break

    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a message over WebSocket."""
        if not self._connected:
            await self.connect()

        if self._ws:
            await self._ws.send_str(json.dumps(message))

    def _handle_subscribe(self, channel: RealtimeChannel) -> None:
        """Handle channel subscribe."""
        pass

    def _handle_unsubscribe(self, channel: RealtimeChannel) -> None:
        """Handle channel unsubscribe."""
        if channel.name in self._channels:
            del self._channels[channel.name]
