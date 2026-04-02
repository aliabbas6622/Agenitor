"""AI Agent orchestrator: uses the Strategy to compute mutations and the CommandManager to apply them."""

from __future__ import annotations

import json
import logging
from typing import Any, List
from uuid import UUID

from app.core.commands import CommandManager
from app.core.commands.timeline_commands import (
    AddClipCommand,
    AddTrackCommand,
    TrimClipCommand,
    MoveClipCommand,
    RemoveClipCommand,
    AddEffectCommand,
    ChangeSpeedCommand,
)
from app.schemas.ir import ClipIR, EffectIR, TimelineIR, TrackType
from app.services.ai.strategy import IAIEngineStrategy

logger = logging.getLogger(__name__)


class AgentService:
    """Orchestrates translating natural language instructions to TimelineIR changes."""

    def __init__(self, engine_strategy: IAIEngineStrategy, command_manager: CommandManager):
        self._strategy = engine_strategy
        self._cmd_manager = command_manager

    async def edit_timeline(self, prompt: str, timeline: TimelineIR) -> TimelineIR:
        """
        Executes a natural language edit against a timeline.
        1. Serializes current timeline
        2. Queries strategy for mutations
        3. Parses mutations into core Commands
        4. Invokes command manager updates
        5. Returns mutated timeline
        """
        logger.info("Agent starting edit: %s", prompt)

        # 1. Ask strategy for actions
        timeline_dict = timeline.model_dump(mode="json")
        result_str = await self._strategy.generate_edits(prompt, timeline_dict)

        # 2. Parse results
        try:
            # Strip backticks if the LLM wrapped it in markdown
            if result_str.startswith("```json"):
                result_str = result_str[7:]
            if result_str.endswith("```"):
                result_str = result_str[:-3]

            operations: List[dict[str, Any]] = json.loads(result_str.strip())
        except json.JSONDecodeError as err:
            logger.error("Failed to parse LLM response as JSON. Response: %s", result_str)
            raise ValueError(f"AI returned invalid JSON: {err}")

        # 3. Apply commands
        logger.info("AI proposed %d operations.", len(operations))

        for op in operations:
            action = op.get("action", "unknown")
            logger.info("Executing Agent Action -> %s: %s", action, op)

            try:
                await self._execute_action(action, op, timeline)
            except ValueError as e:
                logger.warning("Failed to execute action %s: %s", action, e)
                # Continue with other operations even if one fails
            except Exception as e:
                logger.error("Unexpected error executing action %s: %s", action, e)
                raise

        return timeline

    async def _execute_action(self, action: str, op: dict[str, Any], timeline: TimelineIR) -> None:
        """Execute a single action returned by the AI."""

        if action == "AddTrack":
            track_type = TrackType(op.get("track_type", "video"))
            name = op.get("name", "")
            cmd = AddTrackCommand(timeline, track_type, name)
            await self._cmd_manager.execute(cmd)

        elif action == "AddClip":
            track_id = UUID(op["track_id"])
            clip = ClipIR(
                source_path=op.get("source_path", ""),
                track_id=track_id,
                position=op.get("position", 0.0),
                in_point=op.get("in_point", 0.0),
                out_point=op.get("out_point", 10.0),
            )
            cmd = AddClipCommand(timeline, track_id, clip)
            await self._cmd_manager.execute(cmd)

        elif action == "RemoveClip":
            clip_id = UUID(op["clip_id"])
            cmd = RemoveClipCommand(timeline, clip_id)
            await self._cmd_manager.execute(cmd)

        elif action == "TrimClip":
            clip_id = UUID(op["clip_id"])
            new_in = op.get("new_in")
            new_out = op.get("new_out")
            cmd = TrimClipCommand(timeline, clip_id, new_in, new_out)
            await self._cmd_manager.execute(cmd)

        elif action == "MoveClip":
            clip_id = UUID(op["clip_id"])
            new_position = float(op["new_position"])
            cmd = MoveClipCommand(timeline, clip_id, new_position)
            await self._cmd_manager.execute(cmd)

        elif action == "AddEffect":
            clip_id = UUID(op["clip_id"])
            effect_type = op.get("effect_type")
            parameters = op.get("parameters", {})
            effect = EffectIR(type=effect_type, parameters=parameters)
            cmd = AddEffectCommand(timeline, clip_id, effect)
            await self._cmd_manager.execute(cmd)

        elif action == "ChangeSpeed":
            clip_id = UUID(op["clip_id"])
            speed = float(op["speed"])
            cmd = ChangeSpeedCommand(timeline, clip_id, speed)
            await self._cmd_manager.execute(cmd)

        else:
            logger.warning("Unknown action: %s", action)
