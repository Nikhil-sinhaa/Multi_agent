import pytest

from llm_pool import LLMPool, is_rate_limit, load_api_keys


class Client:
    def __init__(self, name, error=None):
        self.name, self.error, self.calls = name, error, 0

    def invoke(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        return self.name


RATE = RuntimeError("Error code: 429 - rate_limit_exceeded")


def test_load_keys_reads_numbered_vars_and_skips_blank_and_duplicates():
    env = {"GROQ_API_KEY": "a", "GROQ_API_KEY_2": "b", "GROQ_API_KEY_3": " ", "GROQ_API_KEY_4": "a"}
    assert load_api_keys(env) == ["a", "b"]
    assert load_api_keys({}) == []


def test_calls_are_spread_round_robin():
    a, b = Client("a"), Client("b")
    pool = LLMPool([a, b])
    assert [pool.invoke([]) for _ in range(4)] == ["a", "b", "a", "b"]
    assert (a.calls, b.calls) == (2, 2)


def test_rate_limited_key_fails_over_to_the_other():
    pool = LLMPool([Client("a", error=RATE), Client("b")])
    assert [pool.invoke([]) for _ in range(3)] == ["b", "b", "b"]


def test_raises_when_every_key_is_rate_limited():
    pool = LLMPool([Client("a", error=RATE), Client("b", error=RATE)])
    with pytest.raises(RuntimeError, match="429"):
        pool.invoke([])


def test_other_errors_are_not_retried_on_another_key():
    a, b = Client("a", error=ValueError("bad request")), Client("b")
    pool = LLMPool([a, b])
    with pytest.raises(ValueError):
        pool.invoke([])
    assert b.calls == 0


def test_single_key_works_and_empty_pool_rejected():
    assert LLMPool([Client("a")]).invoke([]) == "a"
    with pytest.raises(ValueError):
        LLMPool([])


def test_is_rate_limit_detects_groq_errors():
    assert is_rate_limit(RuntimeError("Error code: 413 - Request too large ... rate_limit_exceeded"))
    assert not is_rate_limit(ValueError("invalid json"))
