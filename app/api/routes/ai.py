"""AI interaction endpoints for editing timelines."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession, ProjectSvc
from app.core.commands import CommandManager
from app.services.ai.agent import AgentService
from app.services.ai.strategy import LiteLLMEngineStrategy

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/edit/{project_id}")
async def ai_edit_timeline(
    project_id: str,
    prompt: str,
    db: DbSession,
    project_svc: ProjectSvc,
):
    """
    Submits a natural language instruction to edit a video.
    The AI strategy parses the timeline and returns commands.
    """
    # 1. Fetch current timeline representation
    # Normally we load the full Pydantic model for TimelineIR here.
    # We will assume `project.get_timeline` exists.
    # Currently mocked since our Timeline IR is mostly statically tested.
    timeline_ir = await project_svc.get_timeline(project_id)
    if not timeline_ir:
        # If it's a new project, we construct a blank one.
        from app.schemas.ir import TimelineIR
        timeline_ir = TimelineIR(project_name=f"Project {project_id}", tracks=[], metadata={})
        
    cmd_manager = CommandManager()
    
    # 2. Invoke Strategy (Options like Ollama/OpenAI via LiteLLM)
    # e.g., using a local ollama model: ollama/mistral or gpt-4o
    # Here we hardcode 'gpt-4o' or 'ollama/... as per litellm docs.
    # Let's provide a generic default strategy.
    strategy = LiteLLMEngineStrategy(model_name="gpt-4o")
    
    # 3. Process via Agent
    agent_svc = AgentService(strategy, cmd_manager)
    updated_timeline = await agent_svc.edit_timeline(prompt, timeline_ir)
    
    # 4. Save back to DB
    await project_svc.update_timeline(project_id, updated_timeline)
    
    return {"status": "success", "timeline": updated_timeline}
