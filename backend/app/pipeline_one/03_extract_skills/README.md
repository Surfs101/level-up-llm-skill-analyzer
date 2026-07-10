# Step 03 — Extract skills

**Purpose.** Convert resume text and JD text into canonical skill ids. This is the
single skill-extraction surface, shared with Pipeline 2.

**Inputs (from state).** `resume_text` (step 02) and `jd_text` (an input).

**Outputs (onto state).** `resume_skill_ids` and `jd_skill_ids` — sorted lists of
canonical ids. Normalization is implicit: the FlashText matcher returns canonical
ids directly.

**Failure modes.** None here. An empty result is not an error at this step — the
"no technical skills found" guard lives in step 04, which compares both sets.
