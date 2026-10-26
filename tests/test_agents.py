import pytest

from conftest import FakeLLM

# (node, field it fills)
RESULT_AGENTS = [
    ("flight_agent", "flight_results"),
    ("train_agent", "train_results"),
    ("hotel_agent", "hotel_results"),
    ("weather_agent", "weather_results"),
    ("itinerary_agent", "itinerary"),
]
ALL_AGENTS = [a for a, _ in RESULT_AGENTS] + ["final_agent"]


@pytest.mark.parametrize("agent,key", RESULT_AGENTS)
def test_agent_success_counts_one_llm_call(main_module, base_state, agent, key):
    update = getattr(main_module, agent)(base_state)
    assert update[key] == "LLM REPLY"
    # Reducer is operator.add, so each agent must report only its own call.
    assert update["llm_calls"] == 1


def test_final_agent_success_counts_one_llm_call(main_module, base_state):
    update = main_module.final_agent(base_state)
    assert update["messages"][-1].content == "LLM REPLY"
    assert update["llm_calls"] == 1


@pytest.mark.parametrize("agent,key", RESULT_AGENTS)
def test_agent_failure_does_not_raise(main_module, base_state, monkeypatch, agent, key):
    monkeypatch.setattr(main_module, "llm", FakeLLM(error=RuntimeError("boom")))
    update = getattr(main_module, agent)(base_state)
    assert "boom" in update[key]
    assert update["llm_calls"] == 0


@pytest.mark.parametrize("agent,key", [
    ("train_agent", "train_results"),
    ("hotel_agent", "hotel_results"),
    ("weather_agent", "weather_results"),
])
def test_tool_failure_does_not_raise(main_module, base_state, monkeypatch, agent, key):
    async def broken(*a, **k):
        raise ConnectionError("tool down")

    for name in ("tavily_mcp_search", "aviation_mcp_call",
                 "weather_mcp_search", "forecast_mcp_search"):
        monkeypatch.setattr(main_module, name, broken)
    update = getattr(main_module, agent)(base_state)
    assert "tool down" in update[key]


def test_final_agent_receives_weather(main_module, base_state):
    llm = main_module.llm
    main_module.final_agent(base_state)
    assert "WEATHER" in llm.prompts[-1][-1].content


def test_final_agent_failure_falls_back_to_itinerary(main_module, base_state, monkeypatch):
    monkeypatch.setattr(main_module, "llm", FakeLLM(error=RuntimeError("boom")))
    update = main_module.final_agent(base_state)
    text = update["messages"][-1].content
    assert "boom" in text and "ITINERARY" in text


def test_full_graph_total_llm_calls_and_survives_failure(main_module, monkeypatch):
    """Whole pipeline: 7 successful calls = 6; a failing weather agent does not stop the run."""
    initial = {
        "messages": [], "user_query": "trip", "flight_results": "", "hotel_results": "",
        "train_results": "", "itinerary": "", "weather_results": "", "llm_calls": 0,
    }
    cfg = {"configurable": {"thread_id": "t1"}}
    result = main_module.app.invoke(initial, config=cfg)
    assert result["llm_calls"] == 7   # extraction + 6 agents
    assert result["trip_details"] == {k: "" for k in main_module.TRIP_FIELDS}  # fake reply isn't JSON

    async def broken(city):
        raise ConnectionError("weather down")

    monkeypatch.setattr(main_module, "weather_mcp_search", broken)
    result = main_module.app.invoke(initial, config={"configurable": {"thread_id": "t2"}})
    assert "weather down" in result["weather_results"]
    assert result["llm_calls"] == 6
    assert result["messages"][-1].content == "LLM REPLY"


JSON_REPLY = (
    'Sure! {"origin": "Delhi", "destination": "Tokyo", "start_date": "2027-03-01", '
    '"num_days": 7, "budget": "INR 200000", "travellers": null}'
)


def test_extract_trip_details_parses_json_and_leaves_unknowns_blank(main_module, monkeypatch):
    monkeypatch.setattr(main_module, "llm", FakeLLM(reply=JSON_REPLY))
    d = main_module.extract_trip_details("7 days Delhi to Tokyo")
    assert d["origin"] == "Delhi" and d["num_days"] == "7" and d["travellers"] == ""
    assert main_module.missing_trip_fields(d) == ["travellers"]


def test_extract_trip_details_never_raises(main_module, monkeypatch):
    monkeypatch.setattr(main_module, "llm", FakeLLM(error=RuntimeError("down")))
    assert main_module.missing_trip_fields(main_module.extract_trip_details("x")) == list(main_module.TRIP_FIELDS)


def test_extract_node_skips_llm_when_details_already_supplied(main_module, base_state):
    base_state["trip_details"] = {"destination": "Tokyo"}
    assert main_module.extract_details_agent(base_state) == {"llm_calls": 0}
    assert main_module.llm.prompts == []


@pytest.mark.parametrize("agent", ["flight_agent", "train_agent", "hotel_agent",
                                   "weather_agent", "itinerary_agent", "final_agent"])
def test_every_agent_prompt_contains_trip_details(main_module, base_state, agent):
    base_state["trip_details"] = {"origin": "Delhi", "start_date": "2027-03-01"}
    getattr(main_module, agent)(base_state)
    prompt = main_module.llm.prompts[-1][-1].content
    assert "Departing from: Delhi" in prompt and "Start date: 2027-03-01" in prompt


def test_weather_uses_extracted_destination(main_module, base_state, monkeypatch):
    seen = []

    async def weather(city):
        seen.append(city)
        return "W"

    monkeypatch.setattr(main_module, "weather_mcp_search", weather)
    monkeypatch.setattr(main_module, "forecast_mcp_search", weather)
    monkeypatch.setattr(main_module, "extract_destination",
                        lambda q: pytest.fail("should not need a second LLM call"))
    base_state["trip_details"] = {"destination": "Kyoto"}
    main_module.weather_agent(base_state)
    assert seen == ["Kyoto", "Kyoto"]


def test_flight_agent_searches_the_actual_route_and_dates(main_module, base_state, monkeypatch):
    queries = []

    async def search(q):
        queries.append(q)
        return "DEL-NRT from INR 41,000 (kayak.com)"

    monkeypatch.setattr(main_module, "tavily_mcp_search", search)
    base_state["trip_details"] = {"origin": "Delhi", "destination": "Tokyo", "start_date": "2027-03-01"}
    update = main_module.flight_agent(base_state)

    assert queries and all("Delhi to Tokyo" in q for q in queries)
    assert "2027-03-01" in queries[0]
    prompt = main_module.llm.prompts[-1][-1].content
    assert "INR 41,000 (kayak.com)" in prompt            # real search data reaches the model
    assert "estimate" in prompt                          # and the no-invented-prices rule
    assert update["flight_results"] == "LLM REPLY"


def test_flight_agent_survives_search_outage(main_module, base_state, monkeypatch):
    async def search(q):
        raise ConnectionError("tavily down")

    monkeypatch.setattr(main_module, "tavily_mcp_search", search)
    update = main_module.flight_agent(base_state)
    assert update["flight_results"] == "LLM REPLY"        # still answers, prompt notes failed search
    assert "search failed" in main_module.llm.prompts[-1][-1].content


def test_flight_agent_no_longer_dumps_airport_lists(main_module, base_state, monkeypatch):
    async def boom(*a, **k):
        raise AssertionError("aviation dump should not be used for fares")

    monkeypatch.setattr(main_module, "aviation_mcp_call", boom)
    assert main_module.flight_agent(base_state)["flight_results"] == "LLM REPLY"


def test_train_agent_skipped_when_not_applicable(main_module, base_state, monkeypatch):
    async def boom(*a, **k):
        raise AssertionError("no search expected")

    monkeypatch.setattr(main_module, "tavily_mcp_search", boom)
    base_state["trip_details"] = {"origin": "Delhi", "destination": "Tokyo", "train_applicable": "false"}
    update = main_module.train_agent(base_state)
    assert update["train_results"].startswith("SKIPPED")
    assert update["llm_calls"] == 0
    assert main_module.llm.prompts == []


@pytest.mark.parametrize("details", [{}, {"train_applicable": "true"}, {"train_applicable": ""}])
def test_train_agent_runs_by_default_or_when_applicable(main_module, base_state, details):
    base_state["trip_details"] = details
    update = main_module.train_agent(base_state)
    assert update["train_results"] == "LLM REPLY" and update["llm_calls"] == 1


def test_extraction_reads_train_applicable(main_module, monkeypatch):
    reply = '{"origin":"Delhi","destination":"Tokyo","train_applicable": false}'
    monkeypatch.setattr(main_module, "llm", FakeLLM(reply=reply))
    d = main_module.extract_trip_details("Delhi to Tokyo")
    assert not main_module.train_applicable(d)
    assert "train_applicable" not in main_module.missing_trip_fields(d)   # never asked in the form


def test_full_graph_skips_train_but_still_completes(main_module, monkeypatch):
    reply = '{"origin":"Delhi","destination":"Tokyo","train_applicable": false}'
    monkeypatch.setattr(main_module, "llm", FakeLLM(reply=reply))
    initial = {"messages": [], "user_query": "Delhi to Tokyo", "flight_results": "", "hotel_results": "",
               "train_results": "", "itinerary": "", "weather_results": "", "llm_calls": 0}
    result = main_module.app.invoke(initial, config={"configurable": {"thread_id": "skip"}})
    assert result["train_results"].startswith("SKIPPED")
    assert result["llm_calls"] == 6     # extraction + flight, hotel, weather, itinerary, final
