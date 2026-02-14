import os
import re
import base64
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# ==========================================
# 🔐 Load Environment Variables
# ==========================================
load_dotenv()

FIGMA_TOKEN = os.getenv("FIGMA_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not FIGMA_TOKEN or not OPENROUTER_API_KEY:
    raise Exception("Missing FIGMA_TOKEN or OPENROUTER_API_KEY in .env")

# ==========================================
# 🧠 EXACT REQUIRED VISION PROMPT
# ==========================================
VISION_AGENT_PROMPT = """\
You are the **Initial Planning Agent** of Wirefy, an expert UI/UX analyst with \
deep knowledge of modern web design systems. Your role is to receive a UI \
screenshot and produce a thorough, structured markdown document that fully \
describes the design so that a developer can recreate it without ever seeing the \
original image.

## Your Responsibilities

1. **Page Overview** — Identify the type of page (landing, dashboard, form, etc.) \
and its overall layout structure (sidebar + main, full-width, etc.).

2. **Component Inventory** — List every distinct UI component visible:
   - Navigation bars, sidebars, headers, footers
   - Cards, modals, drawers, tooltips
   - Buttons, inputs, dropdowns, toggles, checkboxes
   - Tables, lists, grids
   - Icons, images, illustrations, avatars
   - Charts, progress bars, badges, tags

3. **Design Tokens** — Extract and document:
   - **Color palette**: primary, secondary, accent, background, surface, text \
colors with approximate hex values
   - **Typography**: font families, sizes, weights, line heights for headings, \
body, captions, labels
   - **Spacing & sizing**: padding, margins, gaps, border-radius values
   - **Shadows & effects**: box-shadows, gradients, blurs, backdrop effects

4. **Layout & Responsiveness** — Describe:
   - Grid/flex structure and column counts
   - Breakpoint expectations (mobile, tablet, desktop)
   - Component positioning and alignment

5. **Interactive Elements** — Note expected behaviors:
   - Hover states, active states, focus states
   - Animations and transitions
   - Navigation flows and routing

6. **Content** — Capture all visible text content, placeholder text, and \
data patterns.

## Output Format

Structure the analysis with clear headers for each section above. Be extremely detailed — \
this document is the single source of truth for the entire build process.

## Rules

- Be precise with color values, sizing, and spacing
- Do NOT make assumptions about hidden UI — only describe what is visible
- Use consistent naming for components across the document
- If something is ambiguous, note it explicitly
- NEVER ask for confirmation or approval
- NEVER say "Shall I proceed?" or similar
- Output ONLY markdown
"""

# ==========================================
# 📌 Extract File Key + Node ID
# ==========================================
def extract_figma_data(figma_link):
    file_key_match = re.search(r'figma.com/design/([^/]+)', figma_link)
    node_id_match = re.search(r'node-id=([^&]+)', figma_link)

    if not file_key_match or not node_id_match:
        raise Exception("Invalid Figma link. Ensure it contains node-id.")

    file_key = file_key_match.group(1)
    node_id = node_id_match.group(1).replace("-", ":")

    return file_key, node_id

# ==========================================
# 📸 Fetch Screenshot from Figma
# ==========================================
def get_figma_image(file_key, node_id):
    url = f"https://api.figma.com/v1/images/{file_key}?ids={node_id}&format=png"
    headers = {"X-Figma-Token": FIGMA_TOKEN}

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception("Figma API Error:\n" + response.text)

    image_url = response.json()["images"].get(node_id)

    if not image_url:
        raise Exception("Unable to retrieve image URL.")

    image_response = requests.get(image_url)

    if image_response.status_code != 200:
        raise Exception("Failed to download image.")

    return base64.b64encode(image_response.content).decode("utf-8")

# ==========================================
# 🤖 LangChain + OpenRouter Vision
# ==========================================
def analyze_with_langchain(base64_image):

    llm = ChatOpenAI(
    model="openai/gpt-4o",
    temperature=0.2,
    max_tokens=1500,   # 👈 VERY IMPORTANT
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base="https://openrouter.ai/api/v1"
)


    messages = [
        SystemMessage(content=VISION_AGENT_PROMPT),
        HumanMessage(content=[
            {"type": "text", "text": "Analyze this UI screenshot thoroughly."},
            {
                "type": "image_url",
                "image_url": f"data:image/png;base64,{base64_image}"
            }
        ])
    ]

    response = llm.invoke(messages)
    return response.content

# ==========================================
# 💾 Save Markdown
# ==========================================
def save_markdown(content):
    with open("initial_plan.md", "w", encoding="utf-8") as f:
        f.write(content)

# ==========================================
# 🚀 MAIN
# ==========================================
if __name__ == "__main__":

    figma_link = input("Enter Figma Link: ")

    print("Extracting Figma data...")
    file_key, node_id = extract_figma_data(figma_link)

    print("Fetching screenshot from Figma...")
    base64_image = get_figma_image(file_key, node_id)

    print("Analyzing with LangChain + OpenRouter...")
    markdown = analyze_with_langchain(base64_image)

    print("Saving Markdown...")
    save_markdown(markdown)

    print("✅ initial_plan.md generated successfully!")
