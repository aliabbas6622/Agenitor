"""AI Engine Strategies for parsing user intents into timeline mutations.

Implements the Strategy pattern to allow swapping between different LLM providers (e.g., OpenAI, Ollama, Anthropic) seamlessly.
"""

from __future__ import annotations

import abc
import asyncio
import json
import logging
import random
from typing import Any

import litellm

# Provide standard type aliases if needed
litellm.set_verbose = False

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on_exceptions: tuple = (Exception,),
):
    """
    Retry a function with exponential backoff.

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delay
        retry_on_exceptions: Tuple of exceptions to retry on

    Returns:
        Result of the function call
    """
    delay = base_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retry_on_exceptions as e:
            last_exception = e
            if attempt < max_retries:
                # Calculate delay with optional jitter
                sleep_delay = min(delay, max_delay)
                if jitter:
                    sleep_delay = sleep_delay * (0.5 + random.random())

                logger.warning(
                    "Attempt %d failed: %s. Retrying in %.2f seconds...",
                    attempt + 1,
                    e,
                    sleep_delay,
                )
                await asyncio.sleep(sleep_delay)
                delay *= exponential_base
            else:
                logger.error("All %d retries exhausted", max_retries)

    raise last_exception


class IAIEngineStrategy(abc.ABC):
    """Base interface for all AI engines taking natural language and returning timeline mutations."""

    @abc.abstractmethod
    async def generate_edits(self, prompt: str, current_timeline: dict[str, Any]) -> str:
        """
        Takes a user prompt and current timeline state as JSON.
        Must return a string literal representing a JSON array of `Command` dicts.
        """
        raise NotImplementedError


class LiteLLMEngineStrategy(IAIEngineStrategy):
    """LiteLLM-based strategy seamlessly supporting OpenAI, Anthropic, Ollama, etc."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        max_tokens: int = 1000,
        temperature: float = 0.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def generate_edits(self, prompt: str, current_timeline: dict[str, Any]) -> str:
        from app.services.ai.tools import LITELLM_TOOLS, AVAILABLE_TOOLS_MAP

        timeline_json_str = json.dumps(current_timeline, indent=2)

        system_prompt = (
            "You are an AI video editor with access to external tools like Voiceover generation.\n"
            "You receive a user request and the current state of a video timeline.\n"
            "Use tools if necessary (like generating voiceovers for a script). If you use a tool, wait for the result.\n"
            "When all necessary operations and tool calls are finished, you must output ONLY a valid JSON array of edit operations, adhering STRICTLY to the following schema structure.\n"
            "Valid action names: 'AddTrack', 'AddClip', 'TrimClip', 'RemoveClip', etc.\n"
            "If no changes are needed, return an empty array `[]`.\n"
            "If you generated an asset (like audio), be sure to include a command like 'AddClip' incorporating the returned asset path.\n\n"
            "Format:\n"
            "[\n"
            "  {\"action\": \"AddClip\", \"track_id\": \"audio-1\", \"source_path\": \"/tmp/assets/...\", \"position\": 0.0, \"in_point\": 0.0, \"out_point\": 5.0}\n"
            "]"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Timeline state:\n```json\n{timeline_json_str}\n```\nUser request: {prompt}"},
        ]

        async def make_llm_call():
            """Inner function to make the LLM call with retry support."""
            response = await litellm.acompletion(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tools=LITELLM_TOOLS,
                tool_choice="auto",
                response_format={"type": "json_object"} if "gpt" in self.model_name else None,
            )
            return response

        # Max iterations to prevent infinite loops
        for iteration in range(5):
            try:
                # Use retry wrapper for LLM call
                response = await retry_with_backoff(
                    make_llm_call,
                    max_retries=self.max_retries,
                    base_delay=self.retry_delay,
                    retry_on_exceptions=(
                        litellm.exceptions.RateLimitError,
                        litellm.exceptions.APIConnectionError,
                        litellm.exceptions.Timeout,
                        litellm.exceptions.APIError,
                    ),
                )
            except Exception as e:
                logger.error("LLM call failed after retries: %s", e)
                return "[]"

            response_msg = response.choices[0].message
            # Extract content if present, or tool calls
            content = response_msg.content

            # Check if LLM wants to call a function
            if hasattr(response_msg, "tool_calls") and response_msg.tool_calls:
                # Add the assistant's request to the messages array
                messages.append(response_msg.model_dump(exclude_none=True))

                # Execute each requested tool
                for tool_call in response_msg.tool_calls:
                    function_name = tool_call.function.name
                    arguments_str = tool_call.function.arguments
                    tool_id = tool_call.id

                    try:
                        args = json.loads(arguments_str)
                        if function_name in AVAILABLE_TOOLS_MAP:
                            func = AVAILABLE_TOOLS_MAP[function_name]
                            result_str = func(**args)
                        else:
                            result_str = json.dumps({"error": f"Unknown function {function_name}"})
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})

                    # Append the tool's result to the context
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": function_name,
                        "content": result_str,
                    })
                # Loop continues to let LLM process tool results
            else:
                # No tool calls made, the LLM has given us the final answer
                return content or "[]"

        # Fallback if loop hit max iterations
        return "[]"
