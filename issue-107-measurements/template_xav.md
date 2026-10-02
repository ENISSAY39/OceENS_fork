Rewritten to match the Instructor's v0; your earlier body is kept below.

---

## Lab 1, step 3: how soon a closed survey's summaries are ready

> Fill in every `___`. The assumptions are yours to choose and to defend at the Oral. The code facts are the same for everyone.

### 1. Assumptions (mine)

- **A. Jobs per survey:** **_ jobs. Why: _**
- **B. Duration of one job, typically:** **_ s. Read from `metadata_text` of a real generation (smoke-test step 5), on _** (date).
- **C. Programmes clicking "generate" on the same evening:** **_. Why: _**

### 2. The number

|                                           | One survey                | A campaign evening (C surveys) |
| ----------------------------------------- | ------------------------- | ------------------------------ |
| Worst case (every job hits the 120 s cap) | 30 s + A × 120 s = \_\_\_ | 30 s + C × A × 120 s = \_\_\_  |
| Typical                                   | A × B = \_\_\_            | C × A × B = \_\_\_             |

**Against the requirement** (a delay of a few hours is expected; longer is fine if an estimated time is shown rather than a bare "12/45"): **_ fits / does not fit, because _**

### 3. What the code does

Paths are at the repository root on `course-2026`. After packaging (EPF-MDE/OceENS#90) they are under `src/oceens/`.

| Part of the question     | Answer                                                                                                                                                                                                                                 | Where                                                                            |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| What starts the clock    | Clicking "generate" on a **closed** survey, not the close itself. The survey is locked and its jobs are inserted into `summaries` with `http_status = 0`. That table is the queue.                                                     | `routers/summaries.py`, `generate_summaries`                                     |
| How many jobs per survey | One per distinct (open question × module × teacher) that has answers. Module and teacher are NULL for survey-wide questions.                                                                                                           | `routers/summaries.py`, the `group_by` before `rows_to_insert`                   |
| How many run at once     | One. A single daemon takes the first pending row, with no ordering by survey. All surveys share one queue. It sleeps 30 s when the queue is empty. The GPU behind it also generates one at a time and is shared with the GenAI course. | `summaries_generator_daemon.py`, main loop and `POLL_INTERVAL_SECONDS`           |
| How long each can take   | At most 120 s per call, and the time spent waiting for the GPU counts inside it. A failed call is marked 504 and **never retried**, so a timeout means the summary is missing, not only late.                                          | `summaries_generator_daemon.py`, `REQUEST_TIMEOUT_SECONDS` and `process_summary` |
| The second time          | Cached forever (`requests_cache`, POST included, `NEVER_EXPIRE`, fixed seed). Destroying and regenerating with the same prompt and answers is almost instant. A changed prompt costs a full rerun.                                     | `services/llm_client.py`, `build_cache_session`                                  |

### 4. The seam that holds this number

**_ (for example: the summaries queue and its one daemon, the one place that could know how long the queue is and give an estimated time). Why this one: _**

_What its callers see is for 2 October, not today._

<details>
<summary>Walk-through: how we got here</summary>

**Q1. What starts the clock?** In `generate_summaries`, a programme manager (or an admin or facilitator) clicks "generate" on a closed survey (`status == 0`). The route sets `status = 2` and inserts one row per job into `summaries` with `http_status = 0`. Nothing is generated at this point. Programme managers ask at the last moment, so the clock that matters starts at the click, not when the survey closes.

**Q2. How many jobs per survey?** The query groups answers to open questions by (question, module, teacher). Each group becomes one job. Count the open questions, the modules each one is asked about, and the teachers per module. Survey-wide questions add one job each.

**Q3. How many run at once?** The daemon loops: it takes `.first()` of the rows with `http_status == 0`, processes it, then takes the next one. There is one daemon and no ordering, so a second survey's jobs queue behind the first's. The GPU generates one at a time anyway, and the GenAI course uses it too.

**Q4. How long can each take?** `ask_model` is called with `timeout=120`. If the GPU is busy, waiting counts inside those 120 s. A timeout ends the job with 504 and it is not retried, so the worst case gives you a missing summary as well as a late one.

**Q5. What happens the second time?** The daemon's HTTP session caches POST requests with no expiry, and the seed is fixed. The same prompt with the same answers is served from the cache. Only a new prompt, or new answers, costs the full time again.

**The arithmetic, with example values.** These are examples, not the answer. Replace them with your own.

- A: 3 open questions × 12 modules × 1.2 teachers, plus a couple of survey-wide questions ≈ **45 jobs**.
- B: take it from `metadata_text` of your own generation. Do not guess it.
- C: say **10** programmes click on the same evening.

Worst case, one survey: 30 s + 45 × 120 s ≈ **1 h 30**. That fits "a few hours".
Worst case, a campaign evening: 10 × 45 = 450 jobs × 120 s ≈ **15 h**. That does not fit. The queue is shared and the clicks cluster at the last moment, and the progress shows "12/45" with no estimated time, so the longer delay is not announced either.
Typical: 45 × B for one survey, 450 × B for the evening. Compare these to the worst case: how far apart they are depends on B.

**Where the number lives.** The one component that sees the queue length and the rate of work is the summaries queue with its one daemon. That makes it a candidate seam for an estimated time. You may argue for another one.

**At the Oral, expect:** _"Show me the assumption that number comes from."_

</details>

🤖 Generated with [Claude Code](https://claude.com/claude-code) · Claude Opus 5.5