from pathlib import Path
import sys
from langchain.messages import HumanMessage, AIMessage

from websockets import State

ROOT=Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from utils.llm_pick import pick_llm 
from utils.database import Database
from Models.schema import AgentSchema, JudgeSchema
from langgraph.graph import StateGraph,START,END




def curate_question(state : AgentSchema) -> AgentSchema:
    # Implement the logic to curate the question based on the state
    # For now, just return the state as is
    llm = pick_llm("low")
    response=state.curated_ques=llm.invoke("Curate the question based on the current state: " + state.user_question).content
    state.curated_ques = response
    state.messages = state.messages + [HumanMessage(content=response)]
    return state

def prompt_query_context(state: AgentSchema) -> AgentSchema:

    db = Database()
    schema_info = db.schema_details("public")
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into Postgres SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications.  
    
    User's Original Query: {state.curated_ques}

    Database Schema Details:
    {schema_info}
    
    """    
    
   
    state.prompt_query_context = prompt
    return state

def generate_sql_query(state: AgentSchema) -> AgentSchema:
        
        prompt=state.prompt_query_context
    
        llm=pick_llm("medium")
        response = llm.invoke(prompt).content
    
        state.generated_sql_query = response
        return state

def is_safe_query(state: AgentSchema) -> AgentSchema:

    sql_query = state.generated_sql_query

    llm = pick_llm("medium")

    llm_judge=llm.with_structured_output(JudgeSchema, method="json_schema")

    prompt=f"""you are sql judge for data security your task is to determine whether the Query is safe to execute or not
    You need to make sure the query only reads from DB and it does not modify any data or structure such as INSERT, UPDATE, DELETE, or DROP
    Mark the query as safe only if it is a valid read-only SQL query. If it is not SQL,
    or could modify data or structure, mark it as unsafe. Explain the decision in comments.
    Heres the SQL Query to evaluate :
    {sql_query}
    """


    response = llm_judge.invoke(prompt)
    state.is_safe=response.is_safe
    state.comments=response.comments


    return state

def canceled_sql(state: AgentSchema) -> AgentSchema:

     comments=state.comments
     state.final_answer = f"Query canceled due to safety concerns The reason provided by the judge is : {comments}"
     state.messages= state.messages + [AIMessage(content=state.final_answer)]
     return state

def execute_sql(state: AgentSchema) -> AgentSchema:
    db = Database()
    query = state.generated_sql_query
    result = db.execute_query(query)
    state.sql_query_execution_result = result
    return state

def represent_final_answer(state: AgentSchema) -> AgentSchema:

    execution_result = state.sql_query_execution_result
    curated_ques = state.curated_ques

    llm=pick_llm("low")

    prompt=f"""You are an SQL analyst. Your task is provide the final answer to user based on execution result of the sql Query which we genrated from users original natural language question. The final answer should be concise and directly address the user's original question. AVoid inculding any SQL Code or technical details.the final answer should be in user friendly format which is easy to understand by non-technical users. if execution result is empty or does not provide a clear answer, politely inform the user that the information could not be retrieved.

    User's Original Question: {curated_ques}
    SQL Query Execution Result: {execution_result}
    """

    response = llm.invoke(prompt).content
    state.final_answer = response

    state.messages= state.messages + [AIMessage(content=response)]

    return state



sql_agent_graph=StateGraph(AgentSchema)
# Nodes
sql_agent_graph.add_node("curate_ques", curate_question)
sql_agent_graph.add_node("prompt_query_context", prompt_query_context)
sql_agent_graph.add_node("generate_sql", generate_sql_query)
sql_agent_graph.add_node("is_safe_sql", is_safe_query)
sql_agent_graph.add_node("canceled_sql", canceled_sql)
sql_agent_graph.add_node("execute_sql", execute_sql)
sql_agent_graph.add_node("represent_final_answer", represent_final_answer)

# Edges
sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql")
sql_agent_graph.add_edge("generate_sql", "is_safe_sql")


def is_safe_edge(state: AgentSchema) -> str:

    is_safe=state.is_safe
    if is_safe.lower() == "yes":
        return "execute_sql"
    else:
        return "canceled_sql"


sql_agent_graph.add_conditional_edges("is_safe_sql", is_safe_edge)
sql_agent_graph.add_edge("canceled_sql",END)
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer",END)


sql_analyst=sql_agent_graph.compile()


if __name__ == "__main__":
  from IPython.display import display,Image

  img = Image(sql_analyst.get_graph().draw_mermaid_png())
  with open("sql_analyst_graph.png", "wb") as f:
      f.write(img.data)

  input_schema={
      "messages": [],
      "user_question": "What are diffrent types of payment methods we have in our database",
      "curated_ques": "",
      "prompt_query_context": "",
      "generated_sql_query": "",
      "is_safe": "No",
      "comments": "",
      "sql_query_execution_result": "",
      "final_answer": ""
  }

  sql_analyst_respone= sql_analyst.invoke(input_schema)
  print(sql_analyst_respone["final_answer"])
