"""Spread LLM calls over several API keys (e.g. one per Groq account).

Groq rate limits are per organization, so keys only add capacity when they
belong to separate accounts.
"""
import itertools
import logging
import os
import threading

logger = logging.getLogger(__name__)


def load_api_keys(env=os.environ) -> list[str]:
    """GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3, ... (blank and duplicate values ignored)."""
    names = ["GROQ_API_KEY"] + [f"GROQ_API_KEY_{i}" for i in range(2, 10)]
    keys = []
    for name in names:
        value = (env.get(name) or "").strip()
        if value and value not in keys:
            keys.append(value)
    return keys


def is_rate_limit(error: Exception) -> bool:
    text = str(error)
    return "429" in text or "413" in text or "rate_limit" in text or "rate limit" in text.lower()


class LLMPool:
    """Round-robins `invoke` over clients; on a rate-limit error tries the next client."""

    def __init__(self, clients):
        if not clients:
            raise ValueError("LLMPool needs at least one client")
        self.clients = list(clients)
        self._counter = itertools.count()
        self._lock = threading.Lock()

    def invoke(self, *args, **kwargs):
        with self._lock:
            start = next(self._counter) % len(self.clients)
        last_error = None
        for offset in range(len(self.clients)):
            index = (start + offset) % len(self.clients)
            try:
                return self.clients[index].invoke(*args, **kwargs)
            except Exception as e:
                if not is_rate_limit(e):
                    raise
                logger.warning("key #%d rate limited, trying next key", index + 1)
                last_error = e
        raise last_error
