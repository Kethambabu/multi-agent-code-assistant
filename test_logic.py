import os
from src.config import load_config
from src.llm.huggingface import HuggingFaceLLM
from src.agents.debug import DebugAgent

config = load_config()
llm = HuggingFaceLLM(config.hf)
agent = DebugAgent(llm)

code = """
def find_max(numbers):
    max_val = 0
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val
"""

result = agent.execute(code)
print(result.output)
