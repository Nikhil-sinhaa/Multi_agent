import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# main.py builds a ChatGroq client and a Postgres pool at import time; point both at fakes.
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://unused")


def _install_fake_postgres():
    import psycopg_pool
    import langgraph.checkpoint.postgres as lg_pg
    from langgraph.checkpoint.memory import InMemorySaver

    class FakePool:
        check_connection = None

        def __init__(self, *a, **k):
            pass

    class FakeSaver(InMemorySaver):
        def __init__(self, *a, **k):
            super().__init__()

        def setup(self):
            pass

    psycopg_pool.ConnectionPool = FakePool
    lg_pg.PostgresSaver = FakeSaver


_install_fake_postgres()


class FakeLLM:
    """Stands in for ChatGroq: returns a fixed reply, or raises when `error` is set."""

    def __init__(self, reply="LLM REPLY", error=None):
        self.reply = reply
        self.error = error
        self.prompts = []

    def invoke(self, messages):
        self.prompts.append(messages)
        if self.error:
            raise self.error
        from langchain_core.messages import AIMessage
        return AIMessage(content=self.reply)


@pytest.fixture
def main_module(monkeypatch):
    import main

    async def fake_search(query):
        return "SEARCH DATA"

    async def fake_aviation(tool_name, tool_args=None):
        return "AVIATION DATA"

    async def fake_weather(city):
        return "WEATHER DATA"

    monkeypatch.setattr(main, "llm", FakeLLM())
    monkeypatch.setattr(main, "tavily_mcp_search", fake_search)
    monkeypatch.setattr(main, "aviation_mcp_call", fake_aviation)
    monkeypatch.setattr(main, "weather_mcp_search", fake_weather)
    monkeypatch.setattr(main, "forecast_mcp_search", fake_weather)
    monkeypatch.setattr(main, "extract_destination", lambda q: "Tokyo")
    return main


@pytest.fixture
def base_state():
    return {
        "messages": [],
        "user_query": "7-day Japan trip",
        "flight_results": "FLIGHTS",
        "hotel_results": "HOTELS",
        "train_results": "TRAINS",
        "itinerary": "ITINERARY",
        "weather_results": "WEATHER",
        "llm_calls": 0,
    }
