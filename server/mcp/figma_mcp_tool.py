from langchain.core.tools import tool
from typing import Optional
import httpx
import os

@tool
async def analyze_figma_component(figma_link: str) -> dict:
    """Analyze a Figma component and generate implementation plan.
    
    Args:
    figma_link: Full Figma share link (e.g., https://www.figma.com/design/xxx/name?node-id=38-2)
    
    Returns:
    A dict with analysis results and paths to generated files.
    """
    
    # Your Figma MCP backend URL (could be configurable)
    FIGMA_MCP_URL = os.getenv("FIGMA_MCP_URL", "http://host.docker.internal:8000")
    
    try:
        # Call your existing Figma MCP backend
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FIGMA_MCP_URL}/generate-plan-from-link",
                json={"figma_link": figma_link},
                timeout=60.0  # Longer timeout for AI processing
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # The files are saved in your backend's plans/ directory
                # You might need to mount a shared volume or copy files
                
                return {
                    "success": True,
                    "component_name": result.get("component", {}).get("name"),
                    "plan": result.get("plan"),
                    "saved_files": result.get("saved_files", {}),
                    "message": "Figma component analyzed successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Figma MCP backend error: {response.text}"
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@tool
async def get_figma_component_info(figma_link: str) -> dict:
    """Get raw component info from Figma without generating plan.
    
    Args:
    figma_link: Full Figma share link
    
    Returns:
    Component structure and metadata.
    """
    
    FIGMA_MCP_URL = os.getenv("FIGMA_MCP_URL", "http://host.docker.internal:8000")
    
    try:
        async with httpx.AsyncClient() as client:
            # First parse the link
            parse_response = await client.post(
                f"{FIGMA_MCP_URL}/parse-figma-link",
                json={"figma_link": figma_link}
            )
            
            if parse_response.status_code != 200:
                return {"success": False, "error": "Failed to parse Figma link"}
            
            parsed = parse_response.json()
            
            # Then get analysis
            analyze_response = await client.post(
                f"{FIGMA_MCP_URL}/analyze-from-link",
                json={"figma_link": figma_link}
            )
            
            if analyze_response.status_code == 200:
                result = analyze_response.json()
                return {
                    "success": True,
                    "component": result.get("component_info"),
                    "analysis": result.get("analysis"),
                    "markdown": result.get("markdown")
                }
            else:
                return {"success": False, "error": "Failed to analyze component"}
                
    except Exception as e:
        return {"success": False, "error": str(e)}