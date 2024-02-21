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
            history.add_message(message.to_lc())
            # file messages are only added to history, not passing to llm
            if message.type == "file":
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
                        # There are 2 chains, the outer one is name: PybotAgentExecutor
                        # and the inner one is name: LLMChain
                        chain_run_id = event["run_id"]
                    case "on_chain_end":
                        # Only persist output on the inner chain, as there will be a duplication
                        # between the last inner chain invocation and the outer chain invocation
                        # I will lost the opportunity to persist the intermediate steps here, but
                        # I don't think it's important also I did not find a better solution for now.
                        if event["name"] != "PybotAgentExecutor":
                            msg = ChatMessage(
                                parent_id=chain_run_id,
                                id=event["run_id"],
                                from_="ai",
                                content=event["data"]["output"]["text"],
                                type="text",
                            )
                            history.add_message(msg.to_lc())
                    case "on_llm_start":
                        logger.debug(f"event: {event}")
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
                        logger.debug(f"event: {event}")
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
                        logger.error(f"event: {event}")
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="ai",
                            # TODO: confirm this error field
                            content=f"llm error: {event['data']}",
                            type="error",
                        )
                        await websocket.send_text(msg.model_dump_json())
                    case "on_tool_start":
                        # TODO: send action to frontend and persist to history
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="system",
                            content=event["data"].get("input"),
                            type="text",
                            additional_kwargs={
                                "prefix": f"<|im_start|>{event['name']}\n",
                                "suffix": "<|im_end|>",
                            },
                        )
                        await websocket.send_text(msg.model_dump_json())
                        # history.add_message(msg.to_lc())
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
                        history.add_message(msg.to_lc())
            conv.last_message_at = utcnow()
            await conv.save()
            # summarize if required
            if message.additional_kwargs and message.additional_kwargs.get(
                "require_summarization", False
            ):
                res = await smry_chain.ainvoke(input={})
                title = res[smry_chain.output_key]
                conv.title = title
                await conv.save()
                info_message = InfoMessage(
                    conversation=message.conversation,
                    from_="ai",
                    content={
                        "type": "title-generated",
                        "payload": title,
                    },
                )
                await websocket.send_text(info_message.model_dump_json())
        except WebSocketDisconnect:
            logger.info("websocket disconnected")
            return
        except Exception:
            logger.exception("Something goes wrong")
