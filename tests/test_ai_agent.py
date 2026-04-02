import pytest

from app.core.commands import CommandManager
from app.schemas.ir import TimelineIR
from app.services.ai.agent import AgentService
from app.services.ai.strategy import IAIEngineStrategy


class MockAIEngineStrategy(IAIEngineStrategy):
    """Mock strategy returning a static valid JSON string."""
    def __init__(self, json_to_return: str):
        self.json_to_return = json_to_return

    async def generate_edits(self, prompt: str, current_timeline: dict) -> str:
        return self.json_to_return


@pytest.mark.asyncio
async def test_agent_parses_llm_json():
    # Arrange
    # Simulated markdown wrapped response from LLM
    llm_str = (
        "```json\n"
        "[\n"
        "  {\"action\": \"TrimClip\", \"track_id\": \"vid-1\", \"clip_id\": \"c-1\", \"new_in_point\": 5.0}\n"
        "]\n"
        "```"
    )
    strategy = MockAIEngineStrategy(llm_str)
    cmd_manager = CommandManager()
    agent = AgentService(strategy, cmd_manager)
    
    # Empty basic timeline
    timeline = TimelineIR()
    
    # Act
    # This shouldn't throw an error and should successfully parse JSON.
    updated_timeline = await agent.edit_timeline("trim that clip to 5 seconds", timeline)
    
    # Assert
    assert updated_timeline.id is not None
    # The actual parsing logic just prints logs right now and returns the timeline, 
    # but we verify it doesn't crash on the markdown block and completes cleanly.


@pytest.mark.asyncio
async def test_agent_handles_invalid_json():
    # Arrange
    invalid_str = "Sure! Here is the operation: { `bad json`"
    strategy = MockAIEngineStrategy(invalid_str)
    agent = AgentService(strategy, CommandManager())
    timeline = TimelineIR()
    
    # Act / Assert
    with pytest.raises(ValueError, match="AI returned invalid JSON"):
        await agent.edit_timeline("do something", timeline)
