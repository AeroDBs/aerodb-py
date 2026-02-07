"""
Pytest configuration for async test support.
"""

import pytest


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


pytest_plugins = ('pytest_asyncio',)
