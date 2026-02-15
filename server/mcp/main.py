from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os
from dotenv import load_dotenv
from figma_mcp_client import FigmaMCPBackend
from openrouter_client import OpenRouterClient
from planning_agent_prompt import format_planning_prompt


load_dotenv()

# Global clients
figma_mcp = None
openrouter = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MCP client
    global figma_mcp, openrouter
    print("🚀 Starting up...")
    
    figma_mcp = FigmaMCPBackend()
    openrouter = OpenRouterClient()
    
    await figma_mcp.initialize()
    
    # List available tools
    tools = await figma_mcp.list_available_tools()
    print(f"📋 Available MCP tools: {tools}")
    
    yield  # Server is running here
    
    # Shutdown: Clean up
    print("👋 Shutting down...")
    if figma_mcp:
        await figma_mcp.close()

app = FastAPI(
    title="Figma MCP Backend",
    lifespan=lifespan
)

class AnalyzeRequest(BaseModel):
    file_key: str
    component_id: str

class AnalyzeResponse(BaseModel):
    success: bool
    message: str
    component_info: Optional[dict] = None
    analysis: Optional[str] = None
    markdown: Optional[str] = None
    tools_used: Optional[List[str]] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    return {
        "message": "Figma MCP Backend",
        "status": "running",
        "mcp_mode": "initialized" if figma_mcp and figma_mcp.initialized else "fallback"
    }
    
@app.post("/generate-plan")
async def generate_implementation_plan(request: AnalyzeRequest):
    """Generate implementation plan from Figma component and save files"""
    
    try:
        # First, get the component info using your existing MCP client
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
        
        # Create plans directory if it doesn't exist
        os.makedirs("plans", exist_ok=True)
        
        # Generate filename based on component name and timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        component_name = component_info.get('name', 'component').lower().replace(' ', '_')
        base_filename = f"{component_name}_{timestamp}"
        
        # Parse the plan_analysis to extract implementation_plan and task
        # The AI response contains both sections, we need to split them
        
        # Method 1: Save the complete response as a single file
        complete_file = f"plans/{base_filename}_complete.md"
        with open(complete_file, "w", encoding="utf-8") as f:
            f.write(f"# Implementation Plan for {component_info.get('name')}\n\n")
            f.write(f"## Component Information\n")
            f.write(f"- **File Key**: {request.file_key}\n")
            f.write(f"- **Component ID**: {request.component_id}\n")
            f.write(f"- **Generated**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(plan_analysis)
        
        # Method 2: Try to extract separate files (if the response has clear sections)
        implementation_plan_file = f"plans/{base_filename}_implementation_plan.md"
        task_file = f"plans/{base_filename}_task.md"
        
        # Simple parsing - assume the response has "### Implementation Plan" and "### Task" sections
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
            # If parsing fails, just save the complete file
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
        
        # Save markdown
        os.makedirs("output", exist_ok=True)
        filename = f"output/{request.file_key}_{request.component_id}.md"
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)