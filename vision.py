from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

VISION_AGENT_PROMPT = """
You are an expert UI/UX analyst.

The Figma MCP tools are available in this environment.

Use:
- get_design_context
- get_variable_defs
- get_metadata

to analyze the selected frame and generate a structured markdown document including:

1. Page Overview
2. Component Inventory
3. Design Tokens
4. Layout & Responsiveness
5. Interactive Elements
6. Visible Content

Be extremely detailed.
Output ONLY markdown.
"""

llm = ChatOpenAI(
    model="openai/gpt-4o",
    temperature=0.2,
)

messages = [
    SystemMessage(content=VISION_AGENT_PROMPT),
    HumanMessage(content="Analyze the currently selected Figma frame.")
]

response = llm.invoke(messages)

print(response.content)
