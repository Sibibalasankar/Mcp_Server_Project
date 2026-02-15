from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os
import datetime
from dotenv import load_dotenv

# Your existing imports
from figma_mcp_client import FigmaMCPBackend
from openrouter_client import OpenRouterClient
from planning_agent_prompt import format_planning_prompt
from figma_url_parser import FigmaUrlParser

# New LangChain Agent import
from langchain_agent import LangChainDeepAgent

load_dotenv()

# Global clients
figma_mcp = None
openrouter = None
langchain_agent = None  # New global agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize all clients
    global figma_mcp, openrouter, langchain_agent
    print("🚀 Starting up...")
    
    # Initialize Figma MCP
    figma_mcp = FigmaMCPBackend()
    await figma_mcp.initialize()
    
    # Initialize OpenRouter
    openrouter = OpenRouterClient()
    
    # Initialize LangChain Deep Agent
    print("🤖 Initializing LangChain Deep Agent...")
    langchain_agent = LangChainDeepAgent()
    await langchain_agent.initialize()
    
    # List available MCP tools
    tools = await figma_mcp.list_available_tools()
    print(f"📋 Available MCP tools: {tools}")
    print("✅ All systems initialized successfully")
    
    yield  # Server is running here
    
    # Shutdown: Clean up
    print("👋 Shutting down...")
    if figma_mcp:
        await figma_mcp.close()
    if langchain_agent:
        await langchain_agent.close()
    print("✅ Shutdown complete")

app = FastAPI(
    title="Figma MCP Backend with LangChain Deep Agent",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class AnalyzeRequest(BaseModel):
    file_key: str
    component_id: str

class FigmaLinkRequest(BaseModel):
    figma_link: str
    file_key: Optional[str] = None
    component_id: Optional[str] = None

class AnalyzeResponse(BaseModel):
    success: bool
    message: str
    component_info: Optional[dict] = None
    analysis: Optional[str] = None
    markdown: Optional[str] = None
    tools_used: Optional[List[str]] = None
    error: Optional[str] = None

class AgentQuery(BaseModel):
    query: str

class AgentResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Figma MCP Backend with LangChain Deep Agent",
        "status": "running",
        "mcp_mode": "initialized" if figma_mcp and figma_mcp.initialized else "fallback",
        "agent_ready": langchain_agent is not None
    }

# Figma URL Parser
@app.post("/parse-figma-link")
async def parse_figma_link(request: FigmaLinkRequest):
    """Parse a Figma link and return extracted data"""
    parsed = FigmaUrlParser.parse_url(request.figma_link)
    return parsed

# Analyze from link
@app.post("/analyze-from-link")
async def analyze_from_link(request: FigmaLinkRequest):
    """Analyze a Figma component using a share link"""
    
    try:
        file_key, component_id = FigmaUrlParser.extract_from_share_link(request.figma_link)
        
        if not file_key:
            return {"error": "Could not extract file key from link"}
        
        if not component_id:
            return {"error": "Could not extract component ID from link. Make sure you're sharing a specific component."}
        
        analyze_request = AnalyzeRequest(file_key=file_key, component_id=component_id)
        return await analyze_component(analyze_request)
        
    except Exception as e:
        return {"error": str(e)}

# Generate plan from link
@app.post("/generate-plan-from-link")
async def generate_plan_from_link(request: FigmaLinkRequest):
    """Generate implementation plan from a Figma share link"""
    
    try:
        file_key, component_id = FigmaUrlParser.extract_from_share_link(request.figma_link)
        
        if not file_key:
            return {"error": "Could not extract file key from link"}
        
        if not component_id:
            return {"error": "Could not extract component ID from link. Make sure you're sharing a specific component."}
        
        analyze_request = AnalyzeRequest(file_key=file_key, component_id=component_id)
        return await generate_implementation_plan(analyze_request)
        
    except Exception as e:
        return {"error": str(e)}
    
# Generate implementation plan
@app.post("/generate-plan")
async def generate_implementation_plan(request: AnalyzeRequest):
    """Generate implementation plan from Figma component and save files"""
    
    try:
        # Get component info via MCP
        component_info = await figma_mcp.get_component_info(
            request.file_key,
            request.component_id
        )
        
        if "error" in component_info:
            return {"error": component_info["error"]}
        
        # Format the planning prompt with actual Figma data
        planning_prompt = format_planning_prompt(component_info)
        
        # Use OpenRouter to generate the plan
        plan_analysis = openrouter.analyze_with_prompt(planning_prompt)
        
        # Use workspace paths for Docker integration
        workspace_root = os.getenv("WORKSPACE_ROOT", ".")
        plans_dir = os.getenv("PLANS_DIR", os.path.join(workspace_root, "plans"))
        os.makedirs(plans_dir, exist_ok=True)
        
        # Generate filename based on component name and timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        component_name = component_info.get('name', 'component').lower().replace(' ', '_')
        base_filename = f"{component_name}_{timestamp}"
        
        # Save the complete response as a single file
        complete_file = os.path.join(plans_dir, f"{base_filename}_complete.md")
        with open(complete_file, "w", encoding="utf-8") as f:
            f.write(f"# Implementation Plan for {component_info.get('name')}\n\n")
            f.write(f"## Component Information\n")
            f.write(f"- **File Key**: {request.file_key}\n")
            f.write(f"- **Component ID**: {request.component_id}\n")
            f.write(f"- **Generated**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(plan_analysis)
        
        # Try to extract separate files
        implementation_plan_file = os.path.join(plans_dir, f"{base_filename}_implementation_plan.md")
        task_file = os.path.join(plans_dir, f"{base_filename}_task.md")
        
        # Parse response sections
        if "### Implementation Plan" in plan_analysis and "### Task" in plan_analysis:
            parts = plan_analysis.split("### Task")
            implementation_part = parts[0]
            task_part = "### Task" + parts[1]
            
            with open(implementation_plan_file, "w", encoding="utf-8") as f:
                f.write(f"# Implementation Plan: {component_info.get('name')}\n\n")
                f.write(f"Generated from Figma component: {request.file_key}:{request.component_id}\n\n")
                f.write(implementation_part)
            
            with open(task_file, "w", encoding="utf-8") as f:
                f.write(f"# Task: Implement {component_info.get('name')}\n\n")
                f.write(task_part)
            
            saved_files = {
                "complete": complete_file,
                "implementation_plan": implementation_plan_file,
                "task": task_file
            }
        else:
            saved_files = {
                "complete": complete_file
            }
        
        return {
            "success": True,
            "component": component_info,
            "plan": plan_analysis,
            "saved_files": saved_files,
            "message": "Implementation plan generated and saved"
        }
        
    except Exception as e:
        return {"error": str(e)}   

# List MCP tools
@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    if not figma_mcp:
        return {"tools": [], "count": 0, "mode": "not_initialized"}
    tools = await figma_mcp.list_available_tools()
    return {
        "tools": tools,
        "count": len(tools),
        "mode": "mcp" if figma_mcp.initialized else "fallback"
    }

# Analyze component
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_component(request: AnalyzeRequest):
    """Analyze a Figma component using MCP"""
    
    try:
        if not figma_mcp:
            return AnalyzeResponse(
                success=False,
                message="MCP client not initialized",
                error="Server not properly initialized"
            )
        
        # Get component info via MCP
        component_info = await figma_mcp.get_component_info(
            request.file_key,
            request.component_id
        )
        
        if "error" in component_info:
            return AnalyzeResponse(
                success=False,
                message="Failed to fetch component",
                error=component_info["error"]
            )
        
        # Analyze with OpenRouter
        analysis = openrouter.analyze_design(component_info)
        
        # Generate markdown
        markdown = openrouter.generate_markdown_content(component_info, analysis)
        
        # Use workspace paths for output
        workspace_root = os.getenv("WORKSPACE_ROOT", ".")
        output_dir = os.getenv("OUTPUT_DIR", os.path.join(workspace_root, "output"))
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, f"{request.file_key}_{request.component_id}.md")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        return AnalyzeResponse(
            success=True,
            message="Analysis complete",
            component_info=component_info,
            analysis=analysis,
            markdown=markdown,
            tools_used=["figma_extract_component_info", "openrouter_analysis"]
        )
        
    except Exception as e:
        return AnalyzeResponse(
            success=False,
            message="Analysis failed",
            error=str(e)
        )

# NEW: LangChain Deep Agent endpoint
@app.post("/agent", response_model=AgentResponse)
async def run_agent(query: AgentQuery):
    """Run the LangChain Deep Agent for complex Figma analysis tasks"""
    
    try:
        if not langchain_agent:
            return AgentResponse(
                success=False,
                error="LangChain agent not initialized"
            )
        
        print(f"🤖 Processing agent query: {query.query}")
        result = await langchain_agent.run(query.query)
        
        return AgentResponse(
            success=True,
            response=result
        )
        
    except Exception as e:
        return AgentResponse(
            success=False,
            error=str(e)
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "components": {
            "figma_mcp": "ready" if figma_mcp else "not_ready",
            "openrouter": "ready" if openrouter else "not_ready",
            "langchain_agent": "ready" if langchain_agent else "not_ready"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)