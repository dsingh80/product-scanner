"""Global concurrency cap for the analyze endpoint.

Limits simultaneous LLM pipeline invocations to prevent memory pressure and
API quota spikes when many requests arrive at once. The cap is checked with
semaphore.locked() before acquiring, so requests are rejected immediately
rather than queued, preserving responsiveness under load.
"""

import asyncio

_semaphore: asyncio.Semaphore | None = None


def get_semaphore(limit: int) -> asyncio.Semaphore:
    """Return the global analyze semaphore, initializing on first call."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(limit)
    return _semaphore
