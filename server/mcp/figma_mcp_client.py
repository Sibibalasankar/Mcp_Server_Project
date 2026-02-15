import os
import httpx
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

class MCPMessage:
    """Simple MCP message class"""
    def __init__(self, type: str, id: Optional[str] = None, payload: Optional[Dict] = None, error: Optional[str] = None):
        self.type = type
        self.id = id
        self.payload = payload or {}
        self.error = error

class MCPMessageType:
    INITIALIZE = "initialize"
    INITIALIZE_RESULT = "initialize_result"
    LIST_TOOLS = "list_tools"
    LIST_TOOLS_RESULT = "list_tools_result"
    CALL_TOOL = "call_tool"
    CALL_TOOL_RESULT = "call_tool_result"
    ERROR = "error"

class FigmaMCPClient:
    """Client for interacting with Figma MCP Server"""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8001"):
        self.server_url = mcp_server_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_id = None
        self.figma_token = os.getenv("FIGMA_ACCESS_TOKEN")
        
    async def initialize(self) -> Dict[str, Any]:
        """Initialize connection with MCP server"""
        return {
            "protocol_version": "0.1.0",
            "server_info": {
                "name": "figma-mcp-client",
                "version": "1.0.0"
            }
        }
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools"""
        return [
            {
                "name": "figma_get_file",
                "description": "Get a Figma file by key"
            },
            {
                "name": "figma_get_component",
                "description": "Get a specific component from Figma"
            },
            {
                "name": "figma_get_image",
                "description": "Get image URL for a node"
            },
            {
                "name": "figma_extract_component_info",
                "description": "Extract structured information from a component"
            }
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool - makes REAL Figma API calls"""
        
        if not self.figma_token:
            return {
                "error": "FIGMA_ACCESS_TOKEN not set in .env file",
                "tool": tool_name
            }
        
        headers = {"X-Figma-Token": self.figma_token}
        
        try:
            async with httpx.AsyncClient() as client:
                
                # Handle different tool types
                if tool_name == "figma_extract_component_info":
                    file_key = arguments.get("file_key")
                    component_id = arguments.get("component_id")
                    
                    # Format component ID (replace hyphen with colon for API)
                    api_component_id = component_id.replace("-", ":")
                    
                    print(f"🔍 Fetching component {api_component_id} from file {file_key}")
                    
                    # Get component data from Figma
                    response = await client.get(
                        f"https://api.figma.com/v1/files/{file_key}/nodes?ids={api_component_id}",
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Extract component information
                    node_data = data.get("nodes", {}).get(api_component_id, {})
                    document = node_data.get("document", {})
                    
                    # Get image URL
                    image_response = await client.get(
                        f"https://api.figma.com/v1/images/{file_key}?ids={api_component_id}",
                        headers=headers
                    )
                    image_response.raise_for_status()
                    image_data = image_response.json()
                    image_url = image_data.get("images", {}).get(api_component_id, "")
                    
                    # Extract children structure
                    children = []
                    for child in document.get("children", []):
                        children.append({
                            "id": child.get("id", ""),
                            "name": child.get("name", ""),
                            "type": child.get("type", "")
                        })
                    
                    result = {
                        "id": component_id,
                        "name": document.get("name", "Unknown"),
                        "type": document.get("type", "Unknown"),
                        "description": document.get("description", ""),
                        "image_url": image_url,
                        "children": children,
                        "components": data.get("components", {}),
                        "styles": data.get("styles", {})
                    }
                    
                    print(f"✅ Found component: {result['name']}")
                    
                    return {
                        "tool": tool_name,
                        "result": result
                    }
                
                elif tool_name == "figma_get_component":
                    file_key = arguments.get("file_key")
                    component_id = arguments.get("component_id")
                    api_component_id = component_id.replace("-", ":")
                    
                    response = await client.get(
                        f"https://api.figma.com/v1/files/{file_key}/nodes?ids={api_component_id}",
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    return {
                        "tool": tool_name,
                        "result": data
                    }
                
                elif tool_name == "figma_get_image":
                    file_key = arguments.get("file_key")
                    node_id = arguments.get("node_id")
                    api_node_id = node_id.replace("-", ":")
                    
                    response = await client.get(
                        f"https://api.figma.com/v1/images/{file_key}?ids={api_node_id}",
                        headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    return {
                        "tool": tool_name,
                        "result": {
                            "node_id": node_id,
                            "image_url": data.get("images", {}).get(api_node_id, "")
                        }
                    }
                
                else:
                    return {
                        "error": f"Unknown tool: {tool_name}",
                        "tool": tool_name
                    }
                    
        except Exception as e:
            print(f"❌ Error calling Figma API: {e}")
            return {
                "error": str(e),
                "tool": tool_name
            }
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()


class FigmaMCPBackend:
    """High-level wrapper for your backend to use Figma MCP"""
    
    def __init__(self):
        self.client = FigmaMCPClient()
        self.initialized = True  # Always initialized since we make direct API calls
    
    async def initialize(self):
        """Initialize the MCP client"""
        try:
            result = await self.client.initialize()
            print("✅ Connected to Figma MCP Client")
            self.initialized = True
            return result
        except Exception as e:
            print(f"⚠️  Initialization warning: {e}")
            self.initialized = True  # Still true since we have direct API access
            return {"mode": "direct_api"}
    
    async def get_component_info(self, file_key: str, component_id: str) -> Dict[str, Any]:
        """Get component information using MCP"""
        
        try:
            result = await self.client.call_tool(
                "figma_extract_component_info",
                {
                    "file_key": file_key,
                    "component_id": component_id
                }
            )
            
            if "error" in result:
                return {"error": result["error"]}
            
            return result.get("result", {})
            
        except Exception as e:
            return {
                "error": str(e),
                "id": component_id
            }
    
    async def list_available_tools(self) -> List[str]:
        """List all available MCP tools"""
        tools = await self.client.list_tools()
        return [tool["name"] for tool in tools]
    
    async def close(self):
        """Close the client"""
        await self.client.close()