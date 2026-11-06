import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.sys.path.append(str(ROOT)) 


from utils.llm_pick import pick_llm 
from Models.schema import JudgeSchema, AgentSchema

sql_query = "How are you"

llm = pick_llm("medium")

llm_judge=llm.with_structured_output(JudgeSchema)

prompt=f"""you are sql judge for data security your task is to determine whether the Query is safe to execute or not
You need to make sure the query only reads from DB and it does not modify any data or structure such as INSERT, UPDATE, DELETE, or DROP
If the query is safe to execute then only respond with yes justifying why it is safe, otherwise respond with no and explain the potential risks.
Heres the SQL Query to evaluate :
{sql_query}
"""


response = llm_judge.invoke(prompt)
print(response)



