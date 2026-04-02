import os
from src.config import load_config
from src.llm.huggingface import HuggingFaceLLM
from src.agents.debug import DebugAgent

config = load_config()
llm = HuggingFaceLLM(config.hf)
agent = DebugAgent(llm)

code = """
def broken_func()
    print("missing colon")
"""

result = agent.execute(code)
print(f"Success: {result.success}")
print(f"Error: {result.error}")
print("--- OUTPUT ---")
print(repr(result.output))
print("--------------")
