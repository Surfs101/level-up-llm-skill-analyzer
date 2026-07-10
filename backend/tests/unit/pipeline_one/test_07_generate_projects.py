"""Step 07 (generate projects) — prompts, parallelism, and partial failure.

The LLM client is mocked, so no OpenAI is called. A fake `chat` inspects the prompt
it receives to decide which of the two projects it is and returns tagged Markdown.
"""

import asyncio
import importlib
import uuid

import pytest

from app.common.errors import PipelineStepError
from app.llm.client import ChatResult
from app.pipeline_one.state import PipelineState

projects_step = importlib.import_module("app.pipeline_one.07_generate_projects")
projects_logic = importlib.import_module("app.pipeline_one.07_generate_projects.logic")

MATCHED = ["python", "fastapi"]  # -> "Python", "FastAPI"
COURSE_COVERED = ["rag", "vector-search"]  # -> "RAG", "Vector Search"
JD = "Build and ship backend APIs."


def result_with(text: str) -> ChatResult:
    return ChatResult(
        text=text, model="gpt-4o", prompt_tokens=100, completion_tokens=200, cost_usd=0.0
    )


def is_skillbridge_prompt(messages: list[dict]) -> bool:
    return "BOTH sets together" in messages[0]["content"]


async def test_renders_prompts_with_the_right_variables(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    seen: list[str] = []

    async def fake_chat(
        messages, *, model, temperature=0.7, max_tokens=None, run_id=None
    ) -> ChatResult:  # type: ignore[no-untyped-def]
        seen.append(messages[0]["content"])
        assert model == "gpt-4o"  # the bottleneck model
        assert max_tokens == projects_logic.MAX_OUTPUT_TOKENS  # cost bound
        return result_with("skillbridge" if is_skillbridge_prompt(messages) else "fast-apply")

    monkeypatch.setattr(projects_logic, "chat", fake_chat)

    result = await projects_logic.generate_projects(MATCHED, JD, COURSE_COVERED)

    fast_apply = next(p for p in seen if "BOTH sets together" not in p)
    skillbridge = next(p for p in seen if "BOTH sets together" in p)

    # Display names (not ids), the JD, and the load-bearing "only listed skills" rule.
    assert "Python, FastAPI" in fast_apply
    assert JD in fast_apply
    assert "ONLY the candidate's listed skills" in fast_apply
    assert "not in the list above" in fast_apply
    # Skillbridge also carries the course skills and requires both sets.
    assert "RAG, Vector Search" in skillbridge
    assert "requires BOTH sets together" in skillbridge
    assert "outside these two lists" in skillbridge

    # project_one is fast-apply, project_two is skillbridge.
    assert result.project_one_md == "fast-apply"
    assert result.project_two_md == "skillbridge"


async def test_the_two_calls_run_in_parallel(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    both_started = asyncio.Event()
    started = 0

    async def fake_chat(
        messages, *, model, temperature=0.7, max_tokens=None, run_id=None
    ) -> ChatResult:  # type: ignore[no-untyped-def]
        nonlocal started
        started += 1
        if started == 2:
            both_started.set()
        # Each call blocks until BOTH have started — only possible if they run
        # concurrently (asyncio.gather). Sequential execution would deadlock here.
        await both_started.wait()
        return result_with("ok")

    monkeypatch.setattr(projects_logic, "chat", fake_chat)

    # If the calls were sequential this would hang; the timeout turns that into a fail.
    result = await asyncio.wait_for(
        projects_logic.generate_projects(MATCHED, JD, COURSE_COVERED), timeout=2
    )
    assert result.project_one_md == "ok" and result.project_two_md == "ok"


async def test_one_call_failing_still_yields_a_plan(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def fake_chat(
        messages, *, model, temperature=0.7, max_tokens=None, run_id=None
    ) -> ChatResult:  # type: ignore[no-untyped-def]
        if is_skillbridge_prompt(messages):
            raise RuntimeError("skillbridge call failed after retries")
        return result_with("fast-apply project")

    monkeypatch.setattr(projects_logic, "chat", fake_chat)

    result = await projects_logic.generate_projects(MATCHED, JD, COURSE_COVERED)

    assert result.project_one_md == "fast-apply project"  # the survivor
    assert result.project_two_md == projects_logic.UNAVAILABLE_MD  # placeholder


async def test_both_calls_failing_fails_the_run(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def fake_chat(
        messages, *, model, temperature=0.7, max_tokens=None, run_id=None
    ) -> ChatResult:  # type: ignore[no-untyped-def]
        raise RuntimeError("OpenAI down")

    monkeypatch.setattr(projects_logic, "chat", fake_chat)

    with pytest.raises(PipelineStepError, match="couldn't generate"):
        await projects_logic.generate_projects(MATCHED, JD, COURSE_COVERED)


async def test_run_threads_projects_onto_state(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def fake_chat(
        messages, *, model, temperature=0.7, max_tokens=None, run_id=None
    ) -> ChatResult:  # type: ignore[no-untyped-def]
        return result_with("skillbridge" if is_skillbridge_prompt(messages) else "fast-apply")

    monkeypatch.setattr(projects_logic, "chat", fake_chat)
    state = PipelineState(
        run_id=uuid.uuid4(),
        jd_text=JD,
        matched_ids=MATCHED,
        course_a_covered=COURSE_COVERED,
    )

    new_state = await projects_step.run(state)

    assert new_state.project_one_md == "fast-apply"
    assert new_state.project_two_md == "skillbridge"
