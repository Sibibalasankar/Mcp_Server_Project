"""Simplified LangChain integration with OpenRouter and Figma MCP"""

import os
import json
import re
from typing import Optional, Dict, Any

# Corrected LangChain imports for v1.2.10
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Import your existing clients
from openrouter_client import OpenRouterClient
from figma_mcp_client import FigmaMCPBackend
from figma_url_parser import FigmaUrlParser


# ============================================================
# Simplified LangChain Agent
# ============================================================

class LangChainDeepAgent:
    """Simplified agent that combines LangChain with OpenRouter and Figma MCP"""
    
    def __init__(self, openrouter_api_key: Optional[str] = None):
        """Initialize the agent with clients"""
        self.openrouter_client = OpenRouterClient(api_key=openrouter_api_key)
        self.figma_backend = FigmaMCPBackend()
        self.llm = None
        
    async def initialize(self):
        """Initialize the agent"""
        print("🤖 Initializing Simplified LangChain Agent...")
        
        # Initialize Figma backend
        await self.figma_backend.initialize()
        
        # Initialize LangChain LLM with OpenRouter
        self.llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.openrouter_client.api_key,
            model="openai/gpt-3.5-turbo",
            temperature=0.7,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "LangChain Deep Agent"
            }
        )
        
        print("✅ Simplified LangChain Agent initialized successfully")
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def _extract_link_from_text(self, text: str) -> Optional[str]:
        """Extract Figma link from text"""
        # Look for Figma links specifically
        figma_pattern = r'https?://[^\s]*(figma\.com)[^\s]*'
        match = re.search(figma_pattern, text)
        if match:
            return match.group(0)
        
        # Fallback to any URL
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, text)
        return match.group(0) if match else None
    
    # ============================================================
    # Figma Operations
    # ============================================================
    
    async def parse_link(self, figma_link: str) -> str:
        """Parse a Figma link"""
        try:
            parsed = FigmaUrlParser.parse_url(figma_link)
            
            if parsed.get("is_valid"):
                return f"""
## ✅ Figma Link Parsed Successfully

- **File Key:** `{parsed.get('file_key')}`
- **Component ID:** `{parsed.get('component_id')}`
- **Node ID:** `{parsed.get('node_id')}`

You can now use this component ID with other tools.
"""
            else:
                return f"❌ Error: Invalid Figma link. Please provide a valid Figma share link."
                
        except Exception as e:
            return f"❌ Error parsing link: {str(e)}"
    
    async def analyze_component(self, figma_link: str) -> str:
        """Analyze a Figma component"""
        try:
            # Parse link
            file_key, component_id = FigmaUrlParser.extract_from_share_link(figma_link)
            
            if not file_key or not component_id:
                return "❌ Error: Could not parse Figma link. Please provide a valid Figma share link."
            
            # Get component info
            component_info = await self.figma_backend.get_component_info(
                file_key, component_id
            )
            
            if "error" in component_info:
                return f"❌ Error: {component_info['error']}"
            
            # Analyze with OpenRouter
            analysis = self.openrouter_client.analyze_design(component_info)
            
            # Format response
            children_count = len(component_info.get('children', []))
            children_json = json.dumps(component_info.get('children', []), indent=2)
            
            return f"""
## 🎨 Figma Component Analysis

**Component:** {component_info.get('name', 'Unknown')}
**Type:** {component_info.get('type', 'Unknown')}
**Elements:** {children_count} child elements

### 📊 Design Analysis
{analysis}

### 📁 Component Structure
```json
{children_json}
```

### 🖼️ Image Reference
{component_info.get('image_url', 'No image available')}
"""
            
        except Exception as e:
            return f"❌ Error analyzing Figma component: {str(e)}"
    
    async def generate_plan(self, figma_link: str) -> str:
        """Generate implementation plan"""
        try:
            # Parse link
            file_key, component_id = FigmaUrlParser.extract_from_share_link(figma_link)
            
            if not file_key or not component_id:
                return "❌ Error: Could not parse Figma link. Please provide a valid Figma share link."
            
            # Get component info
            component_info = await self.figma_backend.get_component_info(
                file_key, component_id
            )
            
            if "error" in component_info:
                return f"❌ Error: {component_info['error']}"
            
            # Create planning prompt
            from planning_agent_prompt import format_planning_prompt
            planning_prompt = format_planning_prompt(component_info)
            
            # Generate plan with OpenRouter
            plan = self.openrouter_client.analyze_with_prompt(planning_prompt)
            
            # Format response
            return f"""
## 📋 Implementation Plan for {component_info.get('name', 'Component')}

{plan}

### 📁 Component Summary
- **Name:** {component_info.get('name')}
- **Type:** {component_info.get('type')}
- **Elements:** {len(component_info.get('children', []))}
- **Image:** {component_info.get('image_url', 'No image')}
"""
            
        except Exception as e:
            return f"❌ Error generating plan: {str(e)}"
    
    async def process_general_query(self, query: str) -> str:
        """Process a general query using LangChain"""
        try:
            # Create system message
            system_msg = SystemMessage(content="""You are a helpful assistant specialized in Figma design analysis and web development.
You can help users with:
- Parsing Figma links
- Analyzing Figma components
- Generating implementation plans
- Answering questions about UI/UX design
- Providing coding advice for Next.js and TailwindCSS

Be concise, helpful, and professional in your responses.""")
            
            # Create human message
            human_msg = HumanMessage(content=query)
            
            # Get response from LLM
            response = await self.llm.ainvoke([system_msg, human_msg])
            
            return response.content
            
        except Exception as e:
            return f"❌ Error processing query: {str(e)}"
    
    # ============================================================
    # Main Run Method
    # ============================================================

    async def run(self, input_text: str) -> str:
        """Main method to handle any input"""
        if not self.llm:
            await self.initialize()
        
        # Check if it's a Figma link operation
        link = self._extract_link_from_text(input_text)
        
        if link:
            # Determine what operation to perform
            text_lower = input_text.lower()
            
            if "parse" in text_lower:
                return await self.parse_link(link)
            elif "analyze" in text_lower:
                return await self.analyze_component(link)
            elif "plan" in text_lower or "implement" in text_lower or "generate" in text_lower:
                return await self.generate_plan(link)
            else:
                # If we have a link but unclear operation, analyze by default
                return await self.analyze_component(link)
        
        # No link found, treat as general query
        return await self.process_general_query(input_text)
    
    async def close(self):
        """Clean up resources"""
        await self.figma_backend.close()
        print("👋 Simplified LangChain Agent closed")


# ============================================================
# Test Function
# ============================================================

async def test_agent():
    """Test the Simplified Agent with sample queries"""
    agent = LangChainDeepAgent()
    await agent.initialize()

    test_queries = [
        "Parse this Figma link: https://www.figma.com/design/hFG2EALMP9Rgrn7CVMWvXf/MCP-Test?node-id=38-2",
        "Analyze the Figma component at: https://www.figma.com/design/hFG2EALMP9Rgrn7CVMWvXf/MCP-Test?node-id=38-2",
        "Generate an implementation plan for: https://www.figma.com/design/hFG2EALMP9Rgrn7CVMWvXf/MCP-Test?node-id=38-2",
        "What are best practices for responsive design?",
    ]

    print("\n" + "="*60)
    print("TESTING SIMPLIFIED LANGCHAIN AGENT")
    print("="*60)

    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}: {query}")
        print("-"*60)
        result = await agent.run(query)
        print(result)
        print("-"*60)

    await agent.close()


# ============================================================
# Main execution
# ============================================================

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_agent())
