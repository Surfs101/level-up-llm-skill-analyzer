# Step 06 — Select courses

**Purpose.** Pick the two best courses from the candidates by how much of the gap
they cover, weighted toward higher-priority skills.

**Inputs (from state).** `retrieved_course_ids` (step 05) and `missing_ids` (step 04).

**Outputs (onto state).** `course_a_id` (top score), `course_b_id` (second), and
`course_a_covered` / `course_b_covered` = `course.skills ∩ missing` — the exact
missing skills each covers (feeds step 07). Scoring reuses `app/rag/ranker.py`:
`Σ weight[priority_rank(s)]` over covered skills, `weight = {1:4, 2:3, 3:2, 4:1}`;
ties break on raw coverage count, then shorter `duration_hours`, then `external_id`.

**Asymmetry (§8, deliberate).** Missing skills are *displayed* languages-first, but
in *scoring* a language gap is worth the MOST (weight 4). This is intended.

**Failure modes (§15).** Fewer than two exact-coverage picks → fill the empty
slot(s) by overall coverage of the taxonomy categories present in the gap. A
fallback pick may cover no exact missing skill (its covered set is then empty).
