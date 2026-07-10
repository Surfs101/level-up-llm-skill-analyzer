"""Step 07 logic — two portfolio projects from parallel gpt-4o calls (design §8, §15).

Renders the two prompts (Jinja2 files in this step's prompts/), then fires both
gpt-4o calls at once with asyncio.gather. The calls are independent: if one fails
(after the client's 3 retries) the other still counts, and its slot gets a
placeholder — we only fail the whole run when BOTH fail. Cost is capped by bounding
output tokens and tracked by the client's per-call Logfire logging (§12).

Skill ids come in; only display names go into the prompt text.
"""

import asyncio
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from openai.types.chat import ChatCompletionMessageParam

from app.common.errors import PipelineStepError
from app.llm.client import chat
from app.nlp.taxonomy import get_skill_by_id

from .schemas import GenerateResult

MODEL = "gpt-4o"
# Bounds each response, keeping two calls well under the $0.10/analysis ceiling.
MAX_OUTPUT_TOKENS = 1500

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_env = Environment(
    loader=FileSystemLoader(_PROMPTS_DIR),
    autoescape=False,  # prompt text is Markdown, not HTML — do not escape
    trim_blocks=True,
    lstrip_blocks=True,
)

BOTH_FAILED = "we couldn't generate your projects right now — please try again."
UNAVAILABLE_MD = (
    "## Project unavailable\n\n"
    "We couldn't generate this project right now. Re-run the analysis to try again."
)


async def generate_projects(
    matched_skill_ids: list[str],
    jd_text: str,
    course_a_covered_ids: list[str],
    run_id: uuid.UUID | None = None,
) -> GenerateResult:
    matched_names = _display_names(matched_skill_ids)
    course_names = _display_names(course_a_covered_ids)

    fast_apply_prompt = _env.get_template("project_fast_apply.j2").render(
        matched_skill_names=matched_names, jd_text=jd_text
    )
    skillbridge_prompt = _env.get_template("project_skillbridge.j2").render(
        matched_skill_names=matched_names, jd_text=jd_text, course_a_covered_names=course_names
    )

    project_one, project_two = await _run_both(fast_apply_prompt, skillbridge_prompt, run_id)
    return GenerateResult(project_one_md=project_one, project_two_md=project_two)


async def _run_both(
    fast_apply_prompt: str, skillbridge_prompt: str, run_id: uuid.UUID | None
) -> tuple[str, str]:
    """Run both generations in parallel; fail only if both fail (§15)."""
    outcomes = await asyncio.gather(
        _generate(fast_apply_prompt, run_id),
        _generate(skillbridge_prompt, run_id),
        return_exceptions=True,
    )
    project_one = _project_text(outcomes[0])
    project_two = _project_text(outcomes[1])
    if project_one is None and project_two is None:
        raise PipelineStepError(BOTH_FAILED)
    return project_one or UNAVAILABLE_MD, project_two or UNAVAILABLE_MD


async def _generate(prompt: str, run_id: uuid.UUID | None) -> str:
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": prompt}]
    result = await chat(messages, model=MODEL, max_tokens=MAX_OUTPUT_TOKENS, run_id=run_id)
    return result.text


def _project_text(outcome: str | BaseException) -> str | None:
    """The generated Markdown, or None if that call failed (gather captured the error)."""
    return outcome if isinstance(outcome, str) else None


def _display_names(skill_ids: list[str]) -> list[str]:
    names = []
    for skill_id in skill_ids:
        skill = get_skill_by_id(skill_id)
        names.append(skill.canonical_name if skill else skill_id)
    return names
