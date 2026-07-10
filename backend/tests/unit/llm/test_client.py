"""Unit tests for the LLM chat client — cost accounting and the retry path.

The OpenAI network call is faked; no key, no network. asyncio.sleep is neutered so
tenacity's backoff doesn't actually wait.
"""

from types import SimpleNamespace

import httpx
import pytest
from openai import RateLimitError

from app.llm import client as llm_client
from app.llm.client import ChatResult, chat, compute_cost_usd

MESSAGES = [{"role": "user", "content": "hi"}]


def fake_completion(content: str, prompt_tokens: int, completion_tokens: int) -> SimpleNamespace:
    """A stand-in for an OpenAI ChatCompletion with just the fields we read."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


class FakeCompletions:
    """Records how many times create() was called and delegates to `behavior`."""

    def __init__(self, behavior) -> None:  # type: ignore[no-untyped-def]
        self.calls = 0
        self._behavior = behavior

    async def create(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        return self._behavior(self.calls)


def fake_client_returning(behavior) -> SimpleNamespace:  # type: ignore[no-untyped-def]
    completions = FakeCompletions(behavior)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions), _completions=completions)


def rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return RateLimitError("rate limited", response=response, body=None)


def test_compute_cost_usd_uses_the_price_table() -> None:
    # gpt-4o: $2.50 in / $10.00 out per 1M tokens.
    cost = compute_cost_usd("gpt-4o", prompt_tokens=1000, completion_tokens=500)
    assert cost == pytest.approx((1000 * 2.50 + 500 * 10.00) / 1_000_000)


def test_compute_cost_usd_unknown_model_is_zero() -> None:
    assert compute_cost_usd("some-future-model", 1000, 1000) == 0.0


async def test_chat_returns_text_and_cost(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = fake_client_returning(lambda _call: fake_completion("hello world", 1000, 500))
    monkeypatch.setattr(llm_client, "_client", lambda: client)

    result = await chat(MESSAGES, model="gpt-4o")

    assert isinstance(result, ChatResult)
    assert result.text == "hello world"
    assert result.prompt_tokens == 1000
    assert result.completion_tokens == 500
    assert result.cost_usd == pytest.approx((1000 * 2.50 + 500 * 10.00) / 1_000_000)


async def test_chat_retries_transient_errors_then_succeeds(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", no_sleep)  # don't actually wait between retries

    def behavior(call: int) -> SimpleNamespace:
        if call < 3:
            raise rate_limit_error()
        return fake_completion("recovered", 10, 20)

    client = fake_client_returning(behavior)
    monkeypatch.setattr(llm_client, "_client", lambda: client)

    result = await chat(MESSAGES, model="gpt-4o")

    assert result.text == "recovered"
    assert client._completions.calls == 3  # failed twice, third succeeded


async def test_chat_gives_up_after_three_attempts(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", no_sleep)

    def always_fail(_call: int) -> SimpleNamespace:
        raise rate_limit_error()

    client = fake_client_returning(always_fail)
    monkeypatch.setattr(llm_client, "_client", lambda: client)

    with pytest.raises(RateLimitError):  # the real error surfaces, run will fail
        await chat(MESSAGES, model="gpt-4o")
    assert client._completions.calls == 3
