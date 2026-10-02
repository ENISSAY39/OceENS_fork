import sqlite3
c = sqlite3.connect("database/db_oceens.db")
q = lambda s, *a: c.execute(s, a).fetchall()
print("tables:", [r[0] for r in q("select name from sqlite_master where type='table'")])
print("surveys:", q("select survey_id, status, * from surveys") if q("select 1 from sqlite_master where name='surveys'") else q("select name from sqlite_master where name like '%urvey%'"))
