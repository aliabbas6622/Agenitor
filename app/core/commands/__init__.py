"""Command Pattern — base classes for undoable timeline operations.

Every mutation to the timeline MUST go through a Command object.
No direct state mutation from API handlers or services.
This pattern enables full undo/redo history and AI-driven editing loops.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from typing import Any


class Command(ABC):
    """Base command — every timeline mutation implements this."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for undo history."""
        ...

    @abstractmethod
    async def execute(self) -> Any:
        """Apply the mutation. Must snapshot state for undo."""
        ...

    @abstractmethod
    async def undo(self) -> None:
        """Reverse the mutation using the snapshot."""
        ...


class CommandManager:
    """Maintains undo/redo stacks for a timeline session.

    Usage:
        manager = CommandManager()
        await manager.execute(TrimClipCommand(clip_id, new_duration, timeline))
        await manager.undo()  # reverts the trim
        await manager.redo()  # re-applies the trim
    """

    def __init__(self, max_history: int = 100) -> None:
        self._undo_stack: deque[Command] = deque(maxlen=max_history)
        self._redo_stack: deque[Command] = deque(maxlen=max_history)

    async def execute(self, command: Command) -> Any:
        """Execute a command and push to undo stack. Clears redo stack."""
        result = await command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        return result

    async def undo(self) -> Command | None:
        """Undo the last command. Returns the undone command or None."""
        if not self._undo_stack:
            return None
        command = self._undo_stack.pop()
        await command.undo()
        self._redo_stack.append(command)
        return command

    async def redo(self) -> Command | None:
        """Redo the last undone command. Returns the redone command or None."""
        if not self._redo_stack:
            return None
        command = self._redo_stack.pop()
        await command.execute()
        self._undo_stack.append(command)
        return command

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def history(self) -> list[str]:
        """Return descriptions of commands in undo stack."""
        return [cmd.description for cmd in self._undo_stack]
