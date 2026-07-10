# Step 04 — Gap analysis

**Purpose.** Compare the two skill sets into matched/missing and score the fit.

**Inputs (from state).** `resume_skill_ids` and `jd_skill_ids` from step 03.

**Outputs (onto state).** `matched_ids = resume ∩ jd`; `missing_ids = jd − resume`
sorted by `priority_rank` ascending (languages first, techniques last, ties by id);
`fit_score = round(100 × |matched| / |jd|)`.

**Failure modes (§15).** Zero skills on either side (junk upload or a
soft-skills-only JD — also what would divide by zero) → `PipelineStepError` ("we
couldn't find technical skills…"). This is the pipeline's single zero-skills guard.
