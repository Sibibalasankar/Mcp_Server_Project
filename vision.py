import os
import re
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# ==========================================
# 🔐 Load Environment Variables
# ==========================================
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MCP_SERVER_URL = "http://localhost:3000"

if not OPENROUTER_API_KEY:
    raise Exception("Missing OPENROUTER_API_KEY in .env")

# ==========================================
# 📌 Extract File Key + Node ID From Link
# ==========================================
def extract_figma_data(figma_link):
    file_key_match = re.search(r'figma.com/design/([^/]+)', figma_link)
    node_id_match = re.search(r'node-id=([^&]+)', figma_link)

    if not file_key_match or not node_id_match:
        raise Exception("Invalid Figma link. Must contain node-id.")

    file_key = file_key_match.group(1)
    node_id = node_id_match.group(1).replace("-", ":")

    return file_key, node_id

# ==========================================
# 🛠 MCP JSON-RPC Caller
# ==========================================
def call_mcp_tool(method, params):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }

    response = requests.post(MCP_SERVER_URL, json=payload)

    if response.status_code != 200:
        raise Exception("MCP Server Error:\n" + response.text)

    result = response.json()

    if "error" in result:
        raise Exception("MCP Error:\n" + str(result["error"]))

    return result.get("result")

# ==========================================
# 🧠 Vision Prompt
# ==========================================
VISION_AGENT_PROMPT = """
You are an expert UI/UX analyst.

Using the provided Figma structured data, generate a structured markdown document including:

1. Page Overview
2. Component Inventory
3. Design Tokens
4. Layout & Responsiveness
5. Interactive Elements
6. Visible Content

Be extremely detailed.
Output ONLY markdown.
"""

# ==========================================
# 🤖 LLM Setup
# ==========================================
llm = ChatOpenAI(
    model="openai/gpt-4o",
    temperature=0.2,
    max_tokens=2000,
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base="https://openrouter.ai/api/v1"
)

# ==========================================
# 🚀 MAIN
# ==========================================
if __name__ == "__main__":

    print("⚡ Make sure MCP server is running (docker compose up)")
    figma_link = input("Enter Full Figma Link: ")

    print("Extracting file key and node ID...")
    file_key, node_id = extract_figma_data(figma_link)

    print("Fetching metadata...")
    metadata = call_mcp_tool("get_metadata", {
        "fileKey": file_key,
        "nodeId": node_id
    })

    print("Fetching design context...")
    design_context = call_mcp_tool("get_design_context", {
        "fileKey": file_key,
        "nodeId": node_id
    })

    print("Fetching variable definitions...")
    variables = call_mcp_tool("get_variable_defs", {
        "fileKey": file_key
    })

    messages = [
        SystemMessage(content=VISION_AGENT_PROMPT),
        HumanMessage(content=f"""
FILE KEY: {file_key}
NODE ID: {node_id}

METADATA:
{metadata}

DESIGN CONTEXT:
{design_context}

VARIABLE DEFINITIONS:
{variables}
""")
    ]

    response = llm.invoke(messages)

    with open("initial_plan.md", "w", encoding="utf-8") as f:
        f.write(response.content)

    print("✅ initial_plan.md generated successfully!")
