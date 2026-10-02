import sqlite3
c = sqlite3.connect("database/db_oceens.db")
q = lambda s, *a: c.execute(s, a).fetchall()
for t in ("answers","questions","submissions","summaries","modules","sections","surveys"):
    print(t, [r[1] for r in q(f"pragma table_info({t})")])
print("question types:", q("select question_type, count(*) from questions group by 1"))
for sid, prog in q("select survey_id, program from surveys") if False else q("select survey_id, survey_id from surveys"):
    jobs = q("""select a.question_id, a.module_id, a.teacher from answers a
        join submissions s on s.submission_id=a.submission_id
        join questions qq on qq.question_id=a.question_id
        where s.survey_id=? and qq.question_type='Question_ouverte'
        group by a.question_id, a.module_id, a.teacher""", sid)
    wide = sum(1 for j in jobs if j[1] is None)
    oq = len({j[0] for j in jobs})
    mods = len({j[1] for j in jobs if j[1] is not None})
    mt = len({(j[1], j[2]) for j in jobs if j[1] is not None})
    subs = q("select count(*) from submissions where survey_id=?", sid)[0][0]
    print(f"survey {sid}: jobs={len(jobs)} open_q={oq} survey_wide={wide} modules={mods} module-teacher pairs={mt} submissions={subs}")
print("summaries:", q("select count(*), http_status from summaries group by http_status"))
print("metadata samples:", q("select metadata_text from summaries where metadata_text is not null limit 5"))
