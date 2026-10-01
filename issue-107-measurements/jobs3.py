import sqlite3
c = sqlite3.connect("database/db_oceens.db")
q = lambda s, *a: c.execute(s, a).fetchall()
print("modules per survey:", q("select survey_id, count(*), count(distinct name) from modules group by 1"))
print("sample modules:", q("select name, teacher, one_teacher_in_list from modules where survey_id=1 limit 30"))
print("open q per section:", q("select s.section_type, s.template_id, count(*) from questions qq join sections s on s.section_id=qq.section_id where qq.question_type='Question_ouverte' group by 1,2"))
print("prompts:", q("select * from prompts"))
print("providers:", q("select * from llm_providers"))
