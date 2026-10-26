import os
import types

import pytest
from streamlit.testing.v1 import AppTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend.py")

# What app.stream(..., stream_mode="updates") yields for one full run.
CHUNKS = [
    {"extract_details_agent": {"llm_calls": 0}},
    {"flight_agent": {"flight_results": "FLIGHT TEXT", "llm_calls": 1}},
    {"train_agent": {"train_results": "TRAIN TEXT", "llm_calls": 1}},
    {"hotel_agent": {"hotel_results": "HOTEL TEXT", "llm_calls": 1}},
    {"weather_agent": {"weather_results": "WEATHER TEXT", "llm_calls": 1}},
    {"itinerary_agent": {"itinerary": "ITIN TEXT", "llm_calls": 1}},
    {"final_agent": {"messages": [types.SimpleNamespace(content="FINAL TEXT")], "llm_calls": 1}},
]


@pytest.fixture
def stub_main(monkeypatch):
    """frontend imports main, which needs Postgres and Groq; replace it with a stub."""
    stub = types.ModuleType("main")
    stub.app = types.SimpleNamespace(stream=lambda *a, **k: iter(CHUNKS))
    stub.chat_agent = lambda state: {"chat_answer": ""}
    stub.TRIP_FIELDS = {"origin": "Departing from", "destination": "Destination",
                        "start_date": "Start date", "num_days": "Trip length (days)",
                        "budget": "Budget", "travellers": "Travellers"}
    stub.details = dict(origin="Delhi", destination="Tokyo", start_date="2027-03-01",
                        num_days="7", budget="INR 200000", travellers="2")
    stub.extract_trip_details = lambda q: dict(stub.details)
    stub.missing_trip_fields = lambda d: [k for k in stub.TRIP_FIELDS if not d.get(k)]
    monkeypatch.setitem(__import__("sys").modules, "main", stub)
    return stub


def _run():
    at = AppTest.from_file(FRONTEND, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def _generate(at):
    at.text_area[0].set_value("7-day Japan trip").run()
    next(b for b in at.button if "Generate" in b.label).click().run()
    assert not at.exception, at.exception


def test_each_session_gets_its_own_thread_id(stub_main):
    first = _run().session_state["thread_id"]
    second = _run().session_state["thread_id"]
    assert first != second
    assert first != "aarohi_user"


def test_thread_id_is_stable_within_a_session(stub_main):
    at = _run()
    before = at.session_state["thread_id"]
    at.run()
    assert at.session_state["thread_id"] == before


def test_stream_uses_the_session_thread_id(stub_main):
    seen = {}

    def stream(inputs, config=None, **kw):
        seen["thread_id"] = config["configurable"]["thread_id"]
        return iter(CHUNKS)

    stub_main.app.stream = stream
    at = _run()
    _generate(at)
    assert seen["thread_id"] == at.session_state["thread_id"]


def test_llm_calls_metric_is_the_sum_not_the_last_value(stub_main):
    at = _run()
    _generate(at)
    html = " ".join(m.value for m in at.markdown)
    # 1 preflight extraction + 6 agents reporting 1 each (details node reports 0)
    assert '<div class="metric-val">7</div><div class="metric-lbl">LLM Calls' in html


def test_weather_agent_is_rendered_with_its_results(stub_main):
    at = _run()
    _generate(at)
    text = " ".join(m.value for m in at.markdown)
    assert "WEATHER TEXT" in text
    assert "weather_agent" not in " ".join(str(s.label) for s in at.status)
    assert any("Weather Agent" in str(s.label) for s in at.status)
    assert at.session_state["travel_context"]["weather_results"] == "WEATHER TEXT"


def test_complete_request_runs_straight_through(stub_main):
    at = _run()
    _generate(at)
    assert "Start date" not in [t.label for t in at.text_input]   # no missing-details form
    assert "FINAL TEXT" in " ".join(m.value for m in at.markdown)


def test_missing_details_are_asked_and_passed_to_the_pipeline(stub_main):
    stub_main.details.update(start_date="", travellers="")
    seen = {}

    def stream(inputs, config=None, **kw):
        seen["details"] = inputs["trip_details"]
        return iter(CHUNKS)

    stub_main.app.stream = stream
    at = _run()
    at.text_area[0].set_value("Japan trip").run()
    next(b for b in at.button if "Generate" in b.label).click().run()

    # Paused: form shown for exactly the missing fields, pipeline not started.
    assert "details" not in seen
    labels = [t.label for t in at.text_input]
    assert labels == ["Start date", "Travellers"]

    at.text_input[0].set_value("2027-03-01")
    next(b for b in at.button if b.label == "Continue").click().run()
    assert not at.exception, at.exception
    assert seen["details"]["start_date"] == "2027-03-01"
    assert seen["details"]["travellers"] == ""      # left blank = flexible
    assert seen["details"]["destination"] == "Tokyo"
