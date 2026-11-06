from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import sys 
from pathlib import Path

load_dotenv() 

ROOT=Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

def pick_llm(level: str):

  if level.lower() == "low":
    return ChatGroq(model_name="openai/gpt-oss-20b",temperature=0,reasoning_effort=None)
  elif level.lower() == "medium":
    return ChatGroq(model_name="openai/gpt-oss-120b",temperature=0,reasoning_effort=None)
  elif level.lower() == "high":
    return ChatGroq(model_name="openai/gpt-oss-120b",temperature=0,reasoning_effort=None)
  else:
    raise ValueError("Invalid level specified. Choose 'low', 'medium', or 'high'.")



  