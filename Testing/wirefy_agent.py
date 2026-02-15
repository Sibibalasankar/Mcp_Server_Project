import requests
import re
import base64
import os
from dotenv import load_dotenv

# ==========================================
# 🔐 Load Environment Variables
# ==========================================
load_dotenv()

FIGMA_TOKEN = os.getenv("FIGMA_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not FIGMA_TOKEN or not OPENROUTER_API_KEY:
    raise Exception("❌ Missing environment variables. Check your .env file.")

# ==========================================
# 🧠 Vision Agent Prompt
# ==========================================
VISION_AGENT_PROMPT = """\
You are the **Initial Planning Agent** of Wirefy, an expert UI/UX analyst with deep knowledge of modern web design systems. Your role is to receive a UI screenshot and produce a thorough, structured markdown document that fully describes the design so that a developer can recreate it without ever seeing the original image.

## Your Responsibilities

1. **Page Overview** — Identify the type of page and its overall layout structure.

2. **Component Inventory** — List every distinct UI component visible.

3. **Design Tokens** — Extract:
   - Color palette (with approximate hex values)
   - Typography details
   - Spacing, padding, margins
   - Border radius and shadows

4. **Layout & Responsiveness** — Describe grid/flex structure and alignment.

5. **Interactive Elements** — Note visible interactive components.

6. **Content** — Capture all visible text.

## Rules

- Only describe what is visible
- Do NOT hallucinate hidden UI
- Be precise and structured
- Output ONLY markdown
"""

# ==========================================
# 📌 Extract File Key + Node ID
# ==========================================
def extract_figma_data(figma_link):
    file_key_match = re.search(r'figma.com/design/([^/]+)', figma_link)
    node_id_match = re.search(r'node-id=([^&]+)', figma_link)

    if not file_key_match or not node_id_match:
        raise Exception("❌ Invalid Figma link. Ensure it contains node-id.")

    file_key = file_key_match.group(1)
    node_id = node_id_match.group(1).replace("-", ":")

    return file_key, node_id

# ==========================================
# 📸 Fetch Screenshot from Figma
# ==========================================
def get_figma_image(file_key, node_id):

    url = f"https://api.figma.com/v1/images/{file_key}?ids={node_id}&format=png"

    headers = {
        "X-Figma-Token": FIGMA_TOKEN
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception("❌ Figma API Error:\n" + response.text)

    image_url = response.json()["images"].get(node_id)

    if not image_url:
        raise Exception("❌ Unable to retrieve image URL from Figma response.")

    image_response = requests.get(image_url)

    if image_response.status_code != 200:
        raise Exception("❌ Failed to download image from Figma.")

    return base64.b64encode(image_response.content).decode("utf-8")

# ==========================================
# 🤖 Send to OpenRouter Vision
# ==========================================
def analyze_with_openrouter(base64_image):

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Wirefy Vision Agent"
        },
        json={
            "model": "openai/gpt-4o",
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": VISION_AGENT_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Perform a complete UI planning analysis and strictly follow the system prompt structure."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1500
        }
    )

    if response.status_code != 200:
        raise Exception("❌ OpenRouter Error:\n" + response.text)

    return response.json()["choices"][0]["message"]["content"]

# ==========================================
# 💾 Save Markdown
# ==========================================
def save_markdown(content):
    with open("initial_plan.md", "w", encoding="utf-8") as f:
        f.write(content)

# ==========================================
# 🚀 MAIN EXECUTION
# ==========================================
if __name__ == "__main__":

    figma_link = input("Enter Figma Link: ")

    print("🔍 Extracting Figma data...")
    file_key, node_id = extract_figma_data(figma_link)

    print("📸 Fetching screenshot from Figma...")
    base64_image = get_figma_image(file_key, node_id)

    print("🧠 Analyzing with Vision model...")
    markdown = analyze_with_openrouter(base64_image)

    print("💾 Saving Markdown file...")
    save_markdown(markdown)

    print("✅ initial_plan.md generated successfully!")
