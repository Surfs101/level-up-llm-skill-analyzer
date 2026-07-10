# Step 02 — Filter recent

**Purpose.** Narrow the raw postings to the ones worth storing.

**Inputs (from state).** `fetched` from step 01.

**Outputs (onto state).** `filtered` — postings updated within the last **21 days**
(same window as the step-05 purge) **and** whose location reads as US or Canada.

**Location heuristic.** A US/Canada signal in the free-text location: a full
state/province name, a country marker (`United States`, `USA`, `Canada`, …), a
`City, ST` two-letter code, or a remote-US/CA flag. A posting with no location gives
no signal and is dropped.

**Failure modes.** None that fail the run — non-matching postings are simply dropped
from this cycle.
