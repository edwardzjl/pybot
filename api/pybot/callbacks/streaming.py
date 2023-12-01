from collections import deque
from itertools import islice
from queue import Queue
from typing import Any, Optional
from uuid import UUID

from fastapi import WebSocket
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from pybot.schemas import ChatMessage


class StreamingLLMCallbackHandler(AsyncCallbackHandler):
    """Callback handler for streaming LLM responses."""

    def __init__(self, websocket: WebSocket, conversation_id: str):
        self.websocket = websocket
        self.conversation_id = conversation_id

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=None,
            type="stream/start",
        )
        await self.websocket.send_text(message.model_dump_json())

    async def on_llm_new_token(
        self,
        token: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=token,
            type="stream/text",
        )
        await self.websocket.send_text(message.model_dump_json())

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=None,
            type="stream/end",
        )
        await self.websocket.send_text(message.model_dump_json())
        # send the full message again in case user switched to another tab
        # so that the frontend can update the message
        full_message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=response.generations[0][0].text,
            type="text",
        )
        await self.websocket.send_text(full_message.model_dump_json())

    async def on_llm_error(
        self,
        error: Exception | KeyboardInterrupt,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM errors."""
        message = ChatMessage(
            id=run_id,
            conversation=self.conversation_id,
            from_="ai",
            content=f"llm error: {str(error)}",
            type="error",
        )
        await self.websocket.send_text(message.model_dump_json())


class StreamingThoughtLLMCallbackHandler(StreamingLLMCallbackHandler):
    """Streaming only the 'thought' part to user, instead of the whole LLM generation."""

    def __init__(self, websocket: WebSocket, conversation_id: str):
        super().__init__(websocket, conversation_id)
        # All the possible prefixes of action. When encounter one of them, stop streaming.
        # TODO: the tokens are hard-separated, which looks ugly to me
        self.action_prefixes: list[Queue] = []
        for prefix in [
            ["{", "\n", "   ", ' "', "tool", "_", "name", '":'],
            ["``", "`", "json"],
        ]:
            q = Queue()
            for t in prefix:
                q.put(t)
            self.action_prefixes.append(q)
        # Longest prefix length. I need to preserve this many tokens in last_tokens.
        # All the overflow tokens can be streamed to user.
        self.preserved_length = max([q.qsize() for q in self.action_prefixes])
        self.last_tokens = Queue()  # an FIFO queue of tokens
        # a circuit breaker, which can save some resource after action already reached.
        self.thinking = False

    def push_to_last_tokens(self, token: str) -> str | None:
        """Push a token to last_tokens, and pop one if the queue is full."""
        self.last_tokens.put(token)
        if self.last_tokens.qsize() > self.preserved_length:
            return self.last_tokens.get()

    def action_reached(self) -> int | None:
        """Check if one of the action prefixes is reached.
        Return the index of the prefix if reached, otherwise None.
        """
        for idx, prefix in enumerate(self.action_prefixes):
            if prefix.qsize() < self.last_tokens.qsize():
                deque_slice = deque(islice(self.last_tokens.queue, 0, prefix.qsize()))
                if prefix.queue == deque_slice:
                    return idx
            else:
                if prefix.queue == self.last_tokens.queue:
                    return idx
        return None

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        # Clear the queue
        # TODO: don't know whether there's a better way to do this
        self.last_tokens = Queue()
        self.thinking = True
        await super().on_llm_start(
            serialized,
            prompts,
            run_id=run_id,
            parent_run_id=parent_run_id,
            tags=tags,
            metadata=metadata,
            **kwargs,
        )

    async def on_llm_new_token(
        self,
        token: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        if not self.thinking:
            return

        if popped := self.push_to_last_tokens(token):
            await super().on_llm_new_token(
                popped, run_id=run_id, parent_run_id=parent_run_id, tags=tags, **kwargs
            )

        idx = self.action_reached()
        if idx is not None:  # action reached
            self.thinking = False
            while self.last_tokens.qsize() > self.action_prefixes[idx].qsize():
                await super().on_llm_new_token(
                    self.last_tokens.get(),
                    run_id=run_id,
                    parent_run_id=parent_run_id,
                    tags=tags,
                    **kwargs,
                )
