from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from langchain.agents import AgentExecutor
from langchain.chains.base import Chain
from langchain_community.chat_message_histories import RedisChatMessageHistory
from loguru import logger

from pybot.context import session_id
from pybot.dependencies import MessageHistory, PbAgent, SmryChain, UserIdHeader
from pybot.models import Conversation
from pybot.schemas import ChatMessage, InfoMessage
from pybot.utils import utcnow

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)


@router.websocket("")
@router.websocket("/")
async def chat(
    websocket: WebSocket,
    agent: Annotated[AgentExecutor, Depends(PbAgent)],
    history: Annotated[RedisChatMessageHistory, Depends(MessageHistory)],
    smry_chain: Annotated[Chain, Depends(SmryChain)],
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    await websocket.accept()
    while True:
        try:
            payload: str = await websocket.receive_text()
            message = ChatMessage.model_validate_json(payload)
            conv = await Conversation.get(message.conversation)
            if conv.owner != userid:
                # TODO: I'm not sure whether this is the correct way to handle this.
                # See websocket code definitions here: <https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent/code>
                raise WebSocketException(code=3403, reason="authorization error")
            session_id.set(f"{userid}:{message.conversation}")
            # file messages are only added to history, not passing to llm
            if message.type == "file":
                lc_msg = message.to_lc()
                history.add_message(lc_msg)
                continue
            chain_run_id = None
            async for event in agent.astream_events(
                input={
                    "input": message.content,
                    # create a new date on every message to solve message across days.
                    "date": date.today(),
                },
                include_run_info=True,
                version="v1",
            ):
                logger.trace(f"event: {event}")
                kind = event["event"]
                match kind:
                    case "on_chain_start":
                        # TODO: maybe it's a little hacky
                        chain_run_id = event["run_id"]
                    case "on_llm_start":
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="ai",
                            content=None,
                            type="stream/start",
                        )
                        await websocket.send_text(msg.model_dump_json())
                    case "on_llm_stream":
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="ai",
                            content=event["data"]["chunk"],
                            type="stream/text",
                        )
                        await websocket.send_text(msg.model_dump_json())
                    case "on_llm_end":
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="ai",
                            content=None,
                            type="stream/end",
                        )
                        await websocket.send_text(msg.model_dump_json())
                    case "on_llm_error":
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="ai",
                            content=f"llm error: {event['data']}",
                            type="error",
                        )
                        await websocket.send_text(msg.model_dump_json())
                    case "on_tool_start":
                        # TODO: send action to frontend and persist to history
                        ...
                    case "on_tool_end":
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="system",
                            content=event["data"].get("output"),
                            type="text",
                            additional_kwargs={
                                "prefix": f"<|im_start|>observation\n",
                                "suffix": "<|im_end|>",
                            },
                        )
                        await websocket.send_text(msg.model_dump_json())
                        history.add_message(msg.to_lc())
                    case "on_tool_error":
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="system",
                            # TODO: confirm this error field
                            content=str(event["data"]),
                            type="error",
                        )
                        await websocket.send_text(msg.model_dump_json())
                        # TODO: confirm this error field
                        history.add_message(msg.to_lc())
            conv.updated_at = utcnow()
            await conv.save()
            # summarize if required
            if (
                message.additional_kwargs
                and "require_summarization" in message.additional_kwargs
                and message.additional_kwargs["require_summarization"]
            ):
                res = await smry_chain.ainvoke(input={})
                info_message = InfoMessage(
                    conversation=message.conversation,
                    from_="ai",
                    content={
                        "type": "title-generated",
                        "payload": res[smry_chain.output_key],
                    },
                )
                await websocket.send_text(info_message.model_dump_json())
        except WebSocketDisconnect:
            logger.info("websocket disconnected")
            return
        except Exception as e:
            logger.error(f"Something goes wrong, err: {str(e)}")
