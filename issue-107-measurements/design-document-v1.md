Adapted to the Instructor's v1 ([#105](https://github.com/EPF-MDE/OceENS/issues/105)). Its text is kept as it is; what I add is marked **My check** or **My measurements**. My v0 is kept [above](https://github.com/EPF-MDE/OceENS/issues/107#issuecomment-5928326267).

---

# Design Document v1

No owners' answers this year: every number below is either a written assumption or a measure, and says which. v0 is kept as a comment below.

| Requirement | Number | Where it comes from | Today | Seam |
| --- | --- | --- | --- | --- |
| How soon one survey's summaries are ready, from the click on "generate" | **1 h 30** at most, even in the worst case. Longer only with an estimated time shown | Assumption D | typically about **15 min**, worst case about **1 h 30**, and the progress shows a bare "12/45" | **The summaries queue and its one daemon**: specified in #131, test and module in #132 |
| Programmes clicking "generate" on the same evening | **10** | Assumption C | one shared queue, one daemon, no ordering by survey | the summaries queue and its one daemon |

**The two rows together.** 10 surveys × 45 jobs is 450 jobs in one queue. Typically 450 × 20 s ≈ **2 h 30**, which fits. In the worst case 450 × 120 s ≈ **15 h**, which does not. No deadline on a job brings that back under a few hours. Only an estimated time, shown instead of a bare "12/45", keeps it within D.

**My measurements, on the same two rows.** The requirement and the seam stay the same. What changes is "Today", and it changes the verdict on the first row:

| Requirement | Today, with my measured values (A = 85, B = 22 s, C = 20) | Against the number |
| --- | --- | --- |
| How soon one survey's summaries are ready | typically about **31 min**, worst case about **2 h 50** | The worst case is beyond 1 h 30. The survey I measured needs the estimated time on its own, not only on a campaign evening. |
| Programmes clicking on the same evening | up to **20** majeures can click, 1 700 jobs in the one queue: typically about **10 h 23**, worst case about **56 h 40** | Beyond 1 h 30 even on a normal evening, from the 3rd programme in the queue. |

---

## How soon a closed survey's summaries are ready

> The Group took these assumptions together, so every Design Document holds the same ones. Be ready to defend each one at the Oral.

### 1. Assumptions (the Group's)

- **A. Jobs per survey:** **45**. Assumed. Why: 3 open questions × 12 modules × 1.2 teachers per module, plus a couple of survey-wide questions.
  - **My check: 85 jobs on the survey I measured.** I ran the route's own `group_by` query (`routers/summaries.py`, `generate_summaries`) on survey 1 of the demo database: MDAI5, template `Sondage_Semestriel_2025`, with the real 5A module list. It gives **6 survey-wide** jobs **+ 79** (question × module × teacher) triples: 3 per-module questions × 27 (module, teacher) pairs = 81 possible, 79 with at least one answer. The shape of the Group's formula holds (3 per-module questions, 1.35 teachers per module because 6 of the 20 modules are co-taught). The gap is the module count: 20, not 12. So I defend 45 as a mid-sized programme, and 85 as a 5A majeure measured on this template. The 85 rows are still in my measurement database (see the evidence below).
- **B. Duration of one job, typically:** **20 s**. This one is measured, not assumed: `metadata_text` of a median-sized job on the seeded database read "gemma4:26b … en 18.6s (116.2 token/s)", on 25 September 2026. The largest seeded job took 55 s. Real surveys have more answers per job than the seed, so B is likely to be higher.
  - **My check: my own generation agrees.** Smoke-test step 5, on 25/09/2026 (`gemma4:26b` on Ollama EPF): 10 successful jobs, **median 18 s, mean 22 s**, from 9.1 s to 58.3 s, for example `Réponse synthétisée par gemma4:26b le 25/09/2026 10:33 en 9.1s (117.7 token/s)`. The queue time is a sum of durations, so the mean is the one to multiply by: 22 s moves every typical figure by 10 %. The daemon's wall-clock time per job was only 0.2 to 0.9 s above the `metadata_text` duration.
- **C. Programmes clicking "generate" on the same evening:** **10**. Assumed. Why: programme managers ask at the last moment, so the clicks cluster.
  - **My check: 10 is half of the programmes that can cluster.** `import/Program_list.csv` lists **20 majeures** in 4A and 5A (10 in Cachan, 4 in Montpellier, 2 in Saint-Nazaire, 4 in Troyes). They have module × teacher surveys like the four demo ones (MDAI5, MDAI4, MIAN5, MDID5) and follow the same semester calendar, so their surveys close the same week. If all 20 click, the evening figures double. The 32 other programmes (1A to 3A, bachelors) would only make it worse.
- **D. The requirement:** **one survey's summaries are ready within 1 h 30 of the click, even in the worst case.** Beyond that, only with an estimated time shown, not a bare "12/45". Assumed. Why: 1 h 30 is the worst case the code gives today (section 2), and it is well inside the working day a programme manager plans around.
  - **My check: D is the worst case of A = 45, not of every survey.** 30 s + 45 × 120 s is 1 h 30, so D sits exactly on the Group's A: one more job and the worst case is past it. On the survey I measured, the worst case is 30 s + 85 × 120 s ≈ **2 h 50**, which is 1 h 20 beyond D. I keep D as the requirement. What my A changes is who needs the second half of it: with 85 jobs, a survey alone in the queue can already go beyond 1 h 30, so the estimated time is needed for one survey, not only for a campaign evening.

### 2. The number

|                                           | One survey                     | A campaign evening (C surveys) |
| ----------------------------------------- | ------------------------------ | ------------------------------ |
| Worst case (every job hits the 120 s cap) | 30 s + 45 × 120 s ≈ **1 h 30** | 30 s + 450 × 120 s ≈ **15 h**  |
| Typical                                   | 45 × 20 s ≈ **15 min**         | 450 × 20 s ≈ **2 h 30**        |

**Against the requirement** (D: 1 h 30 for one survey, longer only with an estimated time): one survey fits, but only while no job waits more than 120 s. A campaign evening at worst case does not: the queue is shared, the clicks cluster, and the progress shows "12/45" with no estimated time.

**My measurements:** with my measured values, one survey no longer fits D in the worst case, and the evening fails on a normal night too:

|                                     | One survey: typical / worst case       | A campaign evening: typical / worst case   |
| ----------------------------------- | -------------------------------------- | ------------------------------------------ |
| Group's A and C, my B (22 s)        | 45 × 22 s ≈ **16 min 30** / 1 h 30     | 450 × 22 s ≈ **2 h 45** / 15 h             |
| A = 85, B = 22 s, C = 20 (all mine) | 85 × 22 s ≈ **31 min** / **2 h 50**    | 20 × 85 × 22 s ≈ **10 h 23** / **56 h 40** |

The worst case does not depend on B: it is 30 s + C × A × 120 s. Against D's 1 h 30 (5 400 s):

- **One survey, typical:** fits in both rows. At 22 s a job, 1 h 30 holds 245 jobs, and one survey has 85.
- **One survey, worst case:** fits only up to 45 jobs. My 85 give 2 h 50.
- **A campaign evening, typical:** with the Group's values the queue is past 1 h 30 from the 7th programme (315 × 20 s = 1 h 45). With mine it is past it from the 3rd (255 × 22 s ≈ 1 h 33). The last of the 20 programmes has 19 × 85 = 1 615 jobs ahead of it in the one shared queue.

The progress counters cannot announce any of it: the three dashboards in `routers/pages.py` (`program_manager_dashboard`, `facilitator_dashboard`, `admin_dashboard`, lines 369, 810 and 988) each `group_by(Summary.survey_id)`, so they only count their own survey's rows. They see neither the jobs ahead in the queue nor the rate of work.

### 3. What the code does

Paths are at the repository root on `course-2026`. After packaging (EPF-MDE/OceENS#90) they are under `src/oceens/`.

**My check:** since Lab 2 I work from `course-2026-fallback-clean-bench`, where every path below is under `src/oceens/`. I checked the line numbers I quote on that branch: `routers/pages.py` lines 369, 810 and 988, `templates/template_parts/part_show_surveys.html` line 338, and `summaries_generator_daemon.py` lines 318-319.

| Part of the question     | Answer                                                                                                                                                                                                                                 | Where                                                                            |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| What starts the clock    | Clicking "generate" on a **closed** survey, not the close itself. The survey is locked and its jobs are inserted into `summaries` with `http_status = 0`. That table is the queue.                                                     | `routers/summaries.py`, `generate_summaries`                                     |
| How many jobs per survey | One per distinct (open question × module × teacher) that has answers. Module and teacher are NULL for survey-wide questions.                                                                                                           | `routers/summaries.py`, the `group_by` before `rows_to_insert`                   |
| How many run at once     | One. A single daemon takes the first pending row, with no ordering by survey. All surveys share one queue. It sleeps 30 s when the queue is empty. The GPU behind it also generates one at a time and is shared with the GenAI course. | `summaries_generator_daemon.py`, main loop and `POLL_INTERVAL_SECONDS`           |
| How long each can take   | At most 120 s per call, and the time spent waiting for the GPU counts inside it. A failed call is marked 504 and **never retried**, so a timeout means the summary is missing, not only late.                                          | `summaries_generator_daemon.py`, `REQUEST_TIMEOUT_SECONDS` and `process_summary` |
| The second time          | Cached forever (`requests_cache`, POST included, `NEVER_EXPIRE`, fixed seed). Destroying and regenerating with the same prompt and answers is almost instant. A changed prompt costs a full rerun.                                     | `services/llm_client.py`, `build_cache_session`                                  |

**My measurements** confirm three of its rows:

- **How long each can take: waiting counts inside the 120 s.** The 58.3 s job generated 3 337 tokens at 114.4 token/s, which is 29 s of generation. The other ~29 s was spent outside token generation (loading the model or waiting for the GPU), and it still counts toward the 120 s timeout.
- **How long each can take: never retried.** During my 16 real calls, **6 failed and none were retried**: 2 × HTTP 500 `Ollama: Server disconnected`, then 4 × HTTP 400 `Model 'gemma4:26b' was not found` in 0.1 s each while the server reloaded the model. When the server is down, the daemon does not wait: it empties the queue into failed rows within seconds. Those summaries are missing, not only late. The whole class was running the same step on the same GPU at that time, so 6/16 is one observation, not a rate to plan on.
- **The second time.** I replayed job 1 with the same prompt and answers. It took **0.01 s** (against 9.98 s the first time) and returned the identical `metadata_text`, straight from `cache_llm.db`.

### 4. The seam that holds this number

**The summaries queue and its one daemon.** Why this one: it is the only place that sees both how many jobs are waiting and how fast they are done, so it is the one that could give an estimated time instead of a bare "12/45".

- **What its callers see:** one question, `progress(survey) -> done, total, errors, estimated time left`. Today three dashboards each count done, pending and errors for themselves (`routers/pages.py`: the programme manager's, the facilitator's and the admin's), and a template decides alone what "finished" means (`templates/template_parts/part_show_surveys.html`). The module answers all four, and none of them counts again.
- **The estimate:** every pending job in the queue ahead of the survey, from every survey, × B. For one survey alone in the queue, 45 × 20 s ≈ **15 min**. On a campaign evening, 450 × 20 s ≈ **2 h 30**, shown, not a bare "12/45". It stays within D even if every job hits the cap: 45 × 120 s = **1 h 30**.
- **Why it is a seam: locality, not leverage.** One table and one daemon sit behind it, so there is no second version to plug in today. Delete the module, and the three dashboards each count done, pending and errors again, and the template decides alone what "finished" means.
- **No schema change.** The queue stays the `summaries` table: `http_status` 0 is pending, 200 is done, and anything else is an error.
- The Spec: #131. The first test and the module: #132.

**My check:** the seam is the one I argued for in v0, and my measurements bear on each of its lines.

- **What its callers see: `errors` is not optional.** 6 of my 16 calls failed and were never retried. A survey can therefore be finished with summaries missing, and the estimated time says nothing about that: only `errors` does. The four values have to be shown together.
- **The estimate, with my values.** One survey alone in the queue: 85 × 22 s ≈ **31 min**, where a bare "12/85" says nothing. The last programme of a 20-programme evening: 1 700 × 22 s ≈ **10 h 23**, shown at the click, so the programme manager knows it is for the next morning. The last sentence of the Instructor's line does not hold on my survey: at the cap, 85 × 120 s = **2 h 50**, beyond D. That is the case D's second half exists for, and the estimate is what makes it acceptable.
- **The estimate: which B.** The estimate is a sum of durations, so it should multiply by the mean, not the median: 22 s on my 10 jobs, against 20 s. With 20 s it runs 10 % short. Reading B from `metadata_text` of finished jobs would be reliable: on my calls the daemon's wall-clock time was only 0.2 to 0.9 s above it.
- **The estimate: the whole queue.** The daemon's loop takes `select(Summary).where(Summary.http_status == 0)` and `.first()`, with no `order_by` (`summaries_generator_daemon.py`, lines 318-319). Nothing promises a survey that its jobs come before another's, so counting every pending job from every survey is the only estimate the code can stand behind.
- **The estimate: when the server is down, it is too long, not too short.** My 4 jobs at HTTP 400 took 0.1 to 0.2 s each, not 22 s. The queue then drains into errors faster than announced. The estimate stays on the safe side, and the missing summaries show up in `errors`.
- **No schema change: I agree, with one note on my own data.** In my measurement database I set the 69 jobs I did not generate to `http_status = -1`, a marker of mine. Under "anything else is an error" they would count as 69 errors. That is a property of my throwaway copy, not of the application, and I will say so at the Oral if I show it.
- **Still outside this seam's interface:** the retry of a 500 or a 400. It would belong behind the same seam, and it changes the number: a retried job costs time, a failed one costs a missing summary.
- **The Spec and the ticket:** #131 and #132 are the Instructor's. My Spec is #151. My ticket is not written yet; its number will go here when it is.

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

<details>
<summary>Evidence: the 16 real calls behind my checks (25/09/2026). More details in <code>issue-107-measurements/</code> on my fork</summary>

**How it was measured:** smoke-test step 5 with my own key from locallm.mde.epf.fr, on a throwaway copy of the demo SQLite database. I queued survey 1 with the route's own query (85 rows at `http_status = 0`) and ran the daemon's own `process_summary`, timing each call. Times in `metadata_text` are UTC; start times are Paris time.

**Where the raw data is kept:** in `issue-107-measurements/`, at the root of my fork, on `course-2026` and on `course-2026-fallback-clean-bench`. Its `README.md` says where the directory comes from and what each file proves. The `.db` and `.log` files are ignored by git, so they are only on my machine: I will show them at the Oral, so the generation does not have to be run again.

On my fork:

- `results.jsonl`: for each call, the start time, the wall-clock time, the input and output tokens, and `metadata_text`.
- the scripts that queued and timed the jobs.

On my machine only:

- the throwaway `db_oceens.db`: its `summaries` table holds the 16 `metadata_text` rows exactly as the daemon wrote them, and the 85 rows of survey 1 (my A). The 69 jobs that were not generated are set to `http_status = -1`.
- `cache_llm.db`: the cached responses, which is how the replay took 0.01 s.
- the two logs of the measurement runs.

The query that lists the 16 rows in the local database:

```sql
SELECT summary_id, question_id, module_id, http_status, metadata_text
FROM summaries WHERE http_status NOT IN (0, -1);
```

| # | Job (question × module) | Verbatims | Output tokens | `metadata_text` duration | Wall-clock | Result |
| - | ----------------------- | --------- | ------------- | ------------------------ | ---------- | ------ |
| 1 | Q3, survey-wide | 3 | 866 | 9.1 s | 9.98 s (12:33:35) | 200 |
| 2 | Q4, survey-wide | 3 | 1 256 | 12.9 s | 13.24 s | 200 |
| 3 | Q5, survey-wide | – | – | – | not recorded | **500** Server disconnected |
| 4 | Q8, survey-wide | 3 | 3 337 | 58.3 s | 58.94 s | 200 |
| 5 | Q9, survey-wide | 3 | 1 106 | 11.2 s | 11.66 s | 200 |
| 6 | Q10, survey-wide | 5 | 2 089 | 21.3 s | 21.52 s | 200 |
| 7 | Q14 × module 1 | 3 | 3 486 | 34.8 s | 35.02 s | 200 |
| 8 | Q14 × module 2 | 3 | 1 297 | 13.3 s | 13.59 s | 200 |
| 9 | Q14 × module 3 | 4 | 2 188 | 22.3 s | 22.50 s | 200 |
| 10 | Q14 × module 4 | 4 | 1 674 | 16.8 s | 17.13 s | 200 |
| 11 | Q14 × module 5 | 5 | 1 891 | 18.7 s | 19.24 s | 200 |
| 12 | Q14 × module 6 | 3 | – | – | 28.75 s | **500** Server disconnected |
| 13–16 | Q14 × modules 7 (two teachers), 8, 9 | 3–4 | – | – | 0.11–0.20 s each | **400** model not found |

**What drives B:** output length, not input. Generation speed was steady at 114 to 119 token/s, so duration ≈ output tokens / 116. The output varied from 866 to 3 486 tokens for the same 3 verbatims. Demo jobs have only 3 to 5 verbatims each (212 to 279 input tokens); a real class of about 40 students gives longer inputs and probably longer outputs. This agrees with the Group's note that B is likely to be higher on real surveys.

</details>

Each **My check** above names where its number comes from, and the raw data behind A and B is kept to be shown at the Oral.
