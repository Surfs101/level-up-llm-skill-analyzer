"""Step 05 logic — retrieve course candidates for the gap (design §8 step 5).

A thin wrapper over app/rag/retriever.py: it embeds a query built from the missing
skills and pulls the cosine-nearest courses. We keep only the candidate ids on the
state; step 06 reloads the full candidates by id to rank them.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.retriever import retrieve_candidates

from .schemas import RetrieveResult


async def retrieve(session: AsyncSession, missing_skill_ids: list[str]) -> RetrieveResult:
    candidates = await retrieve_candidates(session, missing_skill_ids)
    return RetrieveResult(retrieved_course_ids=[candidate.id for candidate in candidates])
