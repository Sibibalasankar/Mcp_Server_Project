"""Bridge between your Figma MCP Backend and their Docker/LangChain system"""

import os
import httpx
from typing import Optional, Dict, Any

class FigmaMCPBridge:
    """Tool for their LangChain system to call your Figma backend"""
    
    def __init__(self, backend_url: str = None):
        self.backend_url = backend_url or os.getenv("FIGMA_MCP_URL", "http://localhost:8000")
    
    async def analyze_figma_link(self, figma_link: str) -> Dict[str, Any]:
        """Main method they will call - analyzes a Figma link"""
        
        try:
            async with httpx.AsyncClient() as client:
                # Call your existing endpoint
                response = await client.post(
                    f"{self.backend_url}/generate-plan-from-link",
                    json={"figma_link": figma_link},
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "component_name": result.get("component", {}).get("name"),
                        "plan": result.get("plan"),
                        "files": result.get("saved_files", {}),
                        "message": "Analysis complete"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Error: {response.text}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_component_info(self, figma_link: str) -> Dict[str, Any]:
        """Just get component info without generating plan"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/analyze-from-link",
                    json={"figma_link": figma_link}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "component": result.get("component_info"),
                        "analysis": result.get("analysis")
                    }
                else:
                    return {"success": False, "error": response.text}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}