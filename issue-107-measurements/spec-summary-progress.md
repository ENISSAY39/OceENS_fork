Part of #107, Design Document: how soon a closed survey's summaries are ready. This Spec comes from its [v1](https://github.com/EPF-MDE/OceENS/issues/107#issuecomment-5954586823), section 4: the summaries queue and its one daemon.

## Problem Statement

A program manager clicks "generate" on a closed survey and then reads a bare "12/85". Nothing tells them whether the summaries will be ready in ten minutes or the next morning, and nothing tells them plainly that some summaries failed and will never arrive.

The Design Document allows a delay beyond 1 h 30 (assumption D) only if an estimated time is shown. On the survey I measured, that case is not rare: its 85 jobs take about 31 min on a normal run and up to 2 h 50 if every job hits the 120 s cap. On a campaign evening, the shared queue is past 1 h 30 from the third program that clicks.

The code cannot give an estimate today. Each of the three dashboards (the program manager's, the facilitator's and the admin's) runs its own copy of the same count, for its own survey only: it sees neither the jobs of other surveys waiting in the queue, nor how long a job takes. The survey list's template decides alone what "finished" means. A failed job is never retried: during my 16 real calls, 6 failed, so a survey can be finished with summaries missing.

## Solution

Wherever a survey's progress is shown, it comes with an estimated time left and the number of failed summaries: "12/85, about 26 min left, 1 failed" instead of "12/85". The estimate counts the whole queue, so on a campaign evening the last program to click reads an honest "about 10 h" at the click, not a counter that barely moves.

One module answers the question "how far has this survey's generation got, and how long is left?". The three dashboards and the template ask it, and none of them counts again.

## User Stories

1. As a program manager, I want to see an estimated time left when I click "generate", so that I know whether to wait or to come back later.
2. As a program manager, I want the estimate to include the other surveys waiting in the queue, so that it is not too short on a campaign evening.
3. As a program manager, I want to see an estimate even when it is beyond 1 h 30, so that a long delay is announced and not discovered.
4. As a program manager, I want to see how many summaries failed, so that I know some are missing and not just late.
5. As a program manager, I want a finished survey with failures to say so, so that I do not take "finished" for "complete".
6. As a program manager, I want a survey whose jobs all returned to be shown as finished even if one summary came back empty, so that it does not stay "in progress" forever.
7. As a program manager, I want the estimate to drop to zero once my survey is finished, so that I do not wait for nothing.
8. As a facilitator, I want the same progress and the same estimate as the program manager for the same survey, so that we do not tell each other different things.
9. As an admin, I want the same progress on my dashboard as on the two others, so that I can answer a program manager who asks when it will be ready.
10. As an admin, I want failures counted the same way everywhere, so that an error on one dashboard is an error on all of them.
11. As a program manager, I want a survey with no summaries requested to show no progress and no estimate, so that I am not told something is running.
12. As a developer, I want one place that reads the summaries queue, so that changing what counts as an error is one change, not four.
13. As a developer, I want one place that holds the duration of a job, so that a new measurement changes one value.
14. As a developer, I want to test the estimate with a database session I pass in, so that the test needs no model, no clock and no patched global.
15. As a developer, I want the module to refuse a zero or negative duration, so that it never reports "0 s left" for a queue that is not empty.
16. As the Instructor, I want the Design Document's number checked by a test, so that the estimate is the one the document argues for.

## Implementation Decisions

**A new package, `oceens.summary_progress`.** It depends on `oceens.models` only. The routers import it; it imports no router and no service, so it adds no import cycle.

**Its interface** is one function and one return type:

```python
progress(session, survey_id, seconds_per_job=22) -> SurveyProgress
SurveyProgress(done, total, errors, estimated_seconds_left, finished)
```

**What the module hides**

- How the queue is read. The `summaries` table is the queue: `http_status` 0 is pending, 200 is done, and any other value is an error. The three copies of the count in the dashboards go away.
- What "done" means. Today a job is done when it has summary text. Here it is done when its `http_status` is 200. A 200 with no text is neither done nor an error under today's rule, so its survey never finishes. Under this one it is done.
- What "finished" means: at least one job, and none pending. The template stops deciding it.
- How the estimate is made: every pending job in the queue, from every survey, × the duration of one job. The daemon takes the first pending row with no ordering by survey, so nothing promises a survey that its jobs come before another's. Counting the whole queue is the only estimate the code can stand behind.
- Which duration. The estimate is a sum of durations, so it multiplies by the mean, not the median: 22 s, measured on my 10 successful jobs of 25/09/2026. The Group's assumption B is 20 s, a median. The value lives in one place.

**What its interface promises**

- The session comes from the caller: the route passes its own, a test passes one on an in-memory database.
- `seconds_per_job` is 22 by default. The routes never pass it. A test passes 120 to check the cap.
- `pending` is `total - done - errors`, and `finished` is `total > 0 and pending == 0`.
- `estimated_seconds_left` is the number of pending jobs in the whole queue × `seconds_per_job`. It is 0 once the survey is finished. It is never capped.
- It only reads. It changes no table and no column, never reads the clock, and never calls the model.

**What it promises when things fail**

- A failed job is an error, whatever its code: 504, 500, 400, or any other value, negative ones included. It is never done and never pending, so it adds nothing to the estimate.
- A survey can be finished with errors. `finished` is true as soon as nothing is pending, and the caller reads `errors` to say how many summaries are missing. `finished` alone never means "all summaries are there".
- A survey with no jobs comes back with a `total` of 0, not finished, and an estimate of 0.
- A survey that does not exist comes back the same way. The module does not raise: whether the survey exists is the route's question.
- A `seconds_per_job` of 0 or less raises `ValueError`.
- A database error is not caught. It goes up to the caller as it is.

**The callers.** The three dashboards pass the module's result to the page instead of their own counts. The template reads `finished`, `errors` and the estimate instead of adding counts. The wording on the page stays in French, as the product is.

**No schema change.**

## Testing Decisions

A good test here goes through `progress` only, with the session passed as an argument, and checks what comes back. It does not look at the query, patches no module global, uses no fake LLM and reads no clock.

**The acceptance criterion is the Design Document's number: a survey of 85 jobs just clicked shows about 31 min left, not a bare "0/85". If every job hits the 120 s cap, it shows 2 h 50: beyond 1 h 30, and announced.**

The test fills an in-memory database with 85 pending rows for one survey (my measured A). Through `progress`:

- `total` is 85, `done` and `errors` are 0, `finished` is false, and `estimated_seconds_left` is 1 870 s (85 × 22 s), about 31 min, within 1 h 30 (5 400 s);
- with `seconds_per_job=120`, the same 85 rows give 10 200 s, about 2 h 50. That is beyond 5 400 s, and the test checks it is returned as it is, not capped and not hidden.

It also checks:

- **The shared queue.** With a second survey's 85 pending rows, the first survey's estimate is 3 740 s (170 × 22 s), still within 1 h 30. With a third, it is 5 610 s (255 × 22 s), beyond 1 h 30.
- **A run with failures, as I measured it.** 10 rows at 200, 2 at 500, 4 at 400 and 69 pending: `done` is 10, `errors` is 6, `finished` is false, and the estimate is 1 518 s (69 × 22 s). The 6 failed rows add nothing to it.
- **Finished with errors.** 79 rows at 200, one of them with no summary text, and 6 errors: `finished` is true, `done` is 79, `errors` is 6, and the estimate is 0.
- **No jobs, and no such survey:** `total` is 0, not finished, estimate 0, and no exception.
- **A `seconds_per_job` of 0** raises `ValueError`.

Only `oceens.summary_progress` is tested. Prior art: the tests already in `tests/` call a function directly and check its result, with no running server. This one adds an in-memory database, which none of them needs yet.

The page itself (the three dashboards passing the result, the template showing it) is checked by hand, on a throwaway database.

## Out of Scope

- **Retrying a failed job.** It belongs behind the same seam and it changes the number: a retried job costs time, a failed one costs a missing summary. This Spec only makes the failures visible.
- **Ordering the queue by survey.** The estimate counts the whole queue because the daemon has no order. Giving it one is a later slice.
- **Learning the duration from finished jobs.** The 22 s is a constant here. Reading it from `metadata_text` would be reliable (on my calls the wall-clock time was 0.2 to 0.9 s above it).
- **The per-job cap.** The 120 s in the daemon is untouched. The acceptance criterion only checks what the estimate says at that cap.
- **The daemon.** It still takes one job at a time and writes its row as it does today.
- **A faster outage.** When the model server is down, jobs fail in about 0.1 s each, so the queue drains faster than the estimate says. The estimate stays on the safe side, and this Spec does not correct it.

## Further Notes

- The numbers come from the Design Document v1 and its evidence: A = 85 jobs (the route's own grouping, on survey 1 of the demo database), 22 s mean on 10 successful jobs, 6 failures out of 16 calls, all on 25/09/2026. The raw data is in `issue-107-measurements/` on my fork.
- The Instructor's Spec for the same seam is #131. This one differs on three points: the acceptance number (85 jobs and 22 s, not 45 and 20 s), the estimate beyond 1 h 30 being part of the criterion, and the failure promises.
