"""Async OpenAI chat client — retries, and per-call cost tracking.

The single place the app makes chat completions (Pipeline 1 step 7). It wraps the
OpenAI SDK with:
  - tenacity retries: 3 attempts, exponential backoff 1s/2s/4s, only on transient
    errors (rate limit, timeout, connection, 5xx) — a bad request is not retried
    (§15). After the last attempt the original error propagates and the run fails.
  - cost accounting: usd is computed from token usage, returned on the result, logged
    with Logfire tags (§12), and — when a run_id is given — appended to the llm_calls
    ledger (app/llm/cost_ledger.py).
"""

import time
import uuid
from dataclasses import dataclass

import logfire
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.llm.cost_ledger import record_call

# USD per 1,000,000 tokens, (input, output). Update when OpenAI pricing changes.
PRICE_PER_MILLION_TOKENS = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}

# Errors worth retrying — all transient. Bad requests / auth errors are not here, so
# they surface immediately instead of wasting three attempts.
_RETRYABLE_ERRORS = (
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
)


@dataclass(frozen=True)
class ChatResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


async def chat(
    messages: list[ChatCompletionMessageParam],
    *,
    model: str,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    run_id: uuid.UUID | None = None,
) -> ChatResult:
    """Run one chat completion and return its text plus token/cost accounting.

    Pass run_id to attribute the call in the cost ledger (Pipeline 1 step 7 does).
    """
    started = time.perf_counter()
    completion = await _create_with_retries(
        messages, model=model, temperature=temperature, max_tokens=max_tokens
    )
    latency_ms = round((time.perf_counter() - started) * 1000)

    usage = completion.usage
    prompt_tokens = usage.prompt_tokens if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    cost_usd = compute_cost_usd(model, prompt_tokens, completion_tokens)

    logfire.info(
        "llm.chat",
        run_id=str(run_id) if run_id else None,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )
    if run_id is not None:
        await record_call(run_id, model, prompt_tokens, completion_tokens, cost_usd)

    return ChatResult(
        text=completion.choices[0].message.content or "",
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s, 2s, 4s
    retry=retry_if_exception_type(_RETRYABLE_ERRORS),
    reraise=True,  # after the last attempt, raise the real error so the run fails
)
async def _create_with_retries(
    messages: list[ChatCompletionMessageParam],
    *,
    model: str,
    temperature: float,
    max_tokens: int | None,
) -> ChatCompletion:
    return await _client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def compute_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """USD cost for one call. Unknown models cost 0 (and get flagged in the log)."""
    price = PRICE_PER_MILLION_TOKENS.get(model)
    if price is None:
        logfire.warn("llm.unknown_model_pricing", model=model)
        return 0.0
    input_price, output_price = price
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000


def _client() -> AsyncOpenAI:
    """The chat client. Not cached: tests patch this to inject a fake OpenAI."""
    return AsyncOpenAI(api_key=get_settings().openai_api_key)
