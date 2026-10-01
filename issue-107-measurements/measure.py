"""Measure B: run the daemon's own process_summary on a throwaway copy of the DB."""
import json, os, sqlite3, sys, time
from datetime import datetime

SP = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(SP, "db")
os.environ["LOCAL_DATABASE_DIR"] = DB_DIR
N = int(sys.argv[1]) if len(sys.argv) > 1 else 15
SURVEY = 1

# 1. Queue the jobs exactly like routers/summaries.py::generate_summaries
c = sqlite3.connect(os.path.join(DB_DIR, "db_oceens.db"))
if not c.execute("select count(*) from summaries").fetchone()[0]:
    rows = c.execute("""select a.module_id, a.teacher, a.question_id from answers a
        join submissions s on s.submission_id=a.submission_id
        join questions q on q.question_id=a.question_id
        where s.survey_id=? and q.question_type='Question_ouverte'
        group by a.question_id, a.module_id, a.teacher""", (SURVEY,)).fetchall()
    c.execute("update surveys set status=2 where survey_id=?", (SURVEY,))
    c.executemany("insert into summaries (survey_id,module_id,teacher,question_id,prompt_id,http_status) values (?,?,?,?,1,0)",
                  [(SURVEY, *r) for r in rows])
    c.commit()
print("queued:", c.execute("select count(*) from summaries where http_status=0").fetchone()[0], flush=True)
c.close()

# 2. Run the daemon's code, N jobs, timed
from sqlmodel import Session, select
from markdown_it import MarkdownIt
from oceens import summaries_generator_daemon as d
from oceens.core.database import engine
from oceens.models import Summary
assert DB_DIR.replace("\\", "/") in str(engine.url).replace("\\", "/"), engine.url

http = d.build_cache_session(os.path.join(SP, "cache_llm.db"))
md, checked = MarkdownIt(), {}
out = open(os.path.join(SP, "results.jsonl"), "a", encoding="utf-8")
for i in range(N):
    with Session(engine) as s:
        row = s.exec(select(Summary).where(Summary.http_status == 0)).first()
        if not row:
            break
        n_verb = len(d.load_verbatims(s, row))
        t0 = time.perf_counter(); start = datetime.now().isoformat(timespec="seconds")
        d.process_summary(s, row, http, md, checked)
        wall = time.perf_counter() - t0
        s.refresh(row)
        rec = dict(i=i, summary_id=row.summary_id, question_id=row.question_id, module_id=row.module_id,
                   verbatims=n_verb, start=start, wall_s=round(wall, 2), http_status=row.http_status,
                   in_tok=row.input_tokens, out_tok=row.output_tokens, metadata_text=row.metadata_text)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush()
