import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# ==========================
# 🔹 CONFIGURATION
# ==========================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "openai/gpt-4o"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

app = Flask(__name__)


# ==========================
# 🔹 OPENROUTER CALL
# ==========================

def call_openrouter(messages, tools=None, tool_choice="auto"):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "DeepAgent-App"
    }

    payload = {
    "model": OPENROUTER_MODEL,
    "messages": messages,
    "max_tokens": 1000,   # 🔥 ADD THIS
    "temperature": 0.7
}


    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
     print("STATUS:", response.status_code)
     print("RESPONSE:", response.text)
     raise Exception(response.text)

    return response.json()


# ==========================
# 🔹 MCP TOOL (Replace with real MCP)
# ==========================

def get_design_context(frame_id: str):
    """
    Replace this mock with real MCP integration.
    """

    # Mocked Figma structured output
    return {
        "frame_id": frame_id,
        "name": "Login Screen",
        "components": [
            {"type": "Text", "content": "Welcome Back"},
            {"type": "Input", "placeholder": "Email"},
            {"type": "Input", "placeholder": "Password"},
            {"type": "Button", "label": "Login"}
        ]
    }


def execute_tool(tool_name, arguments):
    if tool_name == "get_design_context":
        return get_design_context(arguments.get("frame_id"))
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# ==========================
# 🔹 TOOL SCHEMA
# ==========================

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_design_context",
            "description": "Extract structured design data from a Figma frame",
            "parameters": {
                "type": "object",
                "properties": {
                    "frame_id": {
                        "type": "string",
                        "description": "ID of the Figma frame"
                    }
                },
                "required": ["frame_id"]
            }
        }
    }
]


# ==========================
# 🔹 DEEP AGENT REASONING LOOP
# ==========================

def deep_agent(user_prompt):

    messages = [
        {
            "role": "system",
            "content": "You are a design documentation AI. Use tools when required and generate clean markdown output."
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    # Step 1: Initial model call
    response = call_openrouter(messages, tools=TOOLS_SCHEMA)

    message = response["choices"][0]["message"]

    # Step 2: Check if model wants to call a tool
    if "tool_calls" in message:

        for tool_call in message["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            tool_result = execute_tool(tool_name, arguments)

            # Append tool call and result
            messages.append(message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(tool_result)
            })

        # Step 3: Final model call after tool execution
        final_response = call_openrouter(messages)

        return final_response["choices"][0]["message"]["content"]

    else:
        return message["content"]


# ==========================
# 🔹 FLASK ROUTE
# ==========================

@app.route("/generate", methods=["POST"])
def generate():

    data = request.json
    prompt = data.get("prompt")

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        result = deep_agent(prompt)
        return jsonify({"response": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================
# 🔹 RUN SERVER
# ==========================

if __name__ == "__main__":
    app.run(debug=True)
