# Design Document v1

No owners' answers this year: every number below is either a written assumption or a measure, and says which. v0 is kept as a comment below.

| Requirement | Number | Where it comes from | Today | Seam |
| --- | --- | --- | --- | --- |
| How soon one survey's summaries are ready, from the click on "generate" | **1 h 30** at most, even in the worst case. Longer only with an estimated time shown | Assumption D | typically about **15 min**, worst case about **1 h 30**, and the progress shows a bare "12/45" | **The summaries queue and its one daemon**: specified in #131, test and module in #132 |
| Programmes clicking "generate" on the same evening | **10** | Assumption C | one shared queue, one daemon, no ordering by survey | the summaries queue and its one daemon |

**The two rows together.** 10 surveys × 45 jobs is 450 jobs in one queue. Typically 450 × 20 s ≈ **2 h 30**, which fits. In the worst case 450 × 120 s ≈ **15 h**, which does not. No deadline on a job brings that back under a few hours. Only an estimated time, shown instead of a bare "12/45", keeps it within D.

---

## How soon a closed survey's summaries are ready

> The Group took these assumptions together, so every Design Document holds the same ones. Be ready to defend each one at the Oral.

### 1. Assumptions (the Group's)

- **A. Jobs per survey:** **45**. Assumed. Why: 3 open questions × 12 modules × 1.2 teachers per module, plus a couple of survey-wide questions.
- **B. Duration of one job, typically:** **20 s**. This one is measured, not assumed: `metadata_text` of a median-sized job on the seeded database read "gemma4:26b … en 18.6s (116.2 token/s)", on 25 September 2026. The largest seeded job took 55 s. Real surveys have more answers per job than the seed, so B is likely to be higher.
- **C. Programmes clicking "generate" on the same evening:** **10**. Assumed. Why: programme managers ask at the last moment, so the clicks cluster.
- **D. The requirement:** **one survey's summaries are ready within 1 h 30 of the click, even in the worst case.** Beyond that, only with an estimated time shown, not a bare "12/45". Assumed. Why: 1 h 30 is the worst case the code gives today (section 2), and it is well inside the working day a programme manager plans around.

### 2. The number

|                                           | One survey                     | A campaign evening (C surveys) |
| ----------------------------------------- | ------------------------------ | ------------------------------ |
| Worst case (every job hits the 120 s cap) | 30 s + 45 × 120 s ≈ **1 h 30** | 30 s + 450 × 120 s ≈ **15 h**  |
| Typical                                   | 45 × 20 s ≈ **15 min**         | 450 × 20 s ≈ **2 h 30**        |

**Against the requirement** (D: 1 h 30 for one survey, longer only with an estimated time): one survey fits, but only while no job waits more than 120 s. A campaign evening at worst case does not: the queue is shared, the clicks cluster, and the progress shows "12/45" with no estimated time.

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

**The summaries queue and its one daemon.** Why this one: it is the only place that sees both how many jobs are waiting and how fast they are done, so it is the one that could give an estimated time instead of a bare "12/45".

- **What its callers see:** one question, `progress(survey) -> done, total, errors, estimated time left`. Today three dashboards each count done, pending and errors for themselves (`routers/pages.py`: the programme manager's, the facilitator's and the admin's), and a template decides alone what "finished" means (`templates/template_parts/part_show_surveys.html`). The module answers all four, and none of them counts again.
- **The estimate:** every pending job in the queue ahead of the survey, from every survey, × B. For one survey alone in the queue, 45 × 20 s ≈ **15 min**. On a campaign evening, 450 × 20 s ≈ **2 h 30**, shown, not a bare "12/45". It stays within D even if every job hits the cap: 45 × 120 s = **1 h 30**.
- **Why it is a seam: locality, not leverage.** One table and one daemon sit behind it, so there is no second version to plug in today. Delete the module, and the three dashboards each count done, pending and errors again, and the template decides alone what "finished" means.
- **No schema change.** The queue stays the `summaries` table: `http_status` 0 is pending, 200 is done, and anything else is an error.
- The Spec: #131. The first test and the module: #132.

<details>
<summary>Walk-through: how we got here</summary>

**Q1. What starts the clock?** In `generate_summaries`, a programme manager (or an admin or facilitator) clicks "generate" on a closed survey (`status == 0`). The route sets `status = 2` and inserts one row per job into `summaries` with `http_status = 0`. Nothing is generated at this point. Programme managers ask at the last moment, so the clock that matters starts at the click, not when the survey closes.

**Q2. How many jobs per survey?** The query groups answers to open questions by (question, module, teacher). Each group becomes one job. Count the open questions, the modules each one is asked about, and the teachers per module. Survey-wide questions add one job each.

**Q3. How many run at once?** The daemon loops: it takes `.first()` of the rows with `http_status == 0`, processes it, then takes the next one. There is one daemon and no ordering, so a second survey's jobs queue behind the first's. The GPU generates one at a time anyway, and the GenAI course uses it too.

**Q4. How long can each take?** `ask_model` is called with `timeout=120`. If the GPU is busy, waiting counts inside those 120 s. A timeout ends the job with 504 and it is not retried, so the worst case gives you a missing summary as well as a late one.

**Q5. What happens the second time?** The daemon's HTTP session caches POST requests with no expiry, and the seed is fixed. The same prompt with the same answers is served from the cache. Only a new prompt, or new answers, costs the full time again.

**The arithmetic, with the Group's assumptions.**

- A: 3 open questions × 12 modules × 1.2 teachers, plus a couple of survey-wide questions ≈ **45 jobs**.
- B: **20 s**, measured from `metadata_text` of a median-sized job on 25 September 2026 (18.6 s; the largest seeded job took 55 s).
- C: **10** programmes click on the same evening.

Worst case, one survey: 30 s + 45 × 120 s ≈ **1 h 30**. That is D, the requirement.
Worst case, a campaign evening: 10 × 45 = 450 jobs × 120 s ≈ **15 h**. That does not fit. The queue is shared and the clicks cluster at the last moment, and the progress shows "12/45" with no estimated time, so the longer delay is not announced either.
Typical: 45 × 20 s ≈ **15 min** for one survey, 450 × 20 s ≈ **2 h 30** for the evening. Both fit. The gap to the worst case is the 120 s cap against a 20 s job: the requirement holds on a normal evening and breaks when the GPU is busy, for instance with the GenAI course.

**Where the number lives.** The one component that sees the queue length and the rate of work is the summaries queue with its one daemon. No deadline on a job brings the campaign evening (about 15 h in the worst case) back under a few hours. Only an estimated time, shown instead of a bare "12/45", keeps it within the requirement, and only the queue knows how many jobs are waiting. That makes the queue the seam for this number. You may argue for another one.

**At the Oral, expect:** _"Show me the assumption that number comes from."_

</details>




