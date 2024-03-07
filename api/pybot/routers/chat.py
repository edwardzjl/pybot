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
from pybot.schemas import AIChatMessage, ChatMessage, InfoMessage
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
            chain_metadata = {
                "conversation_id": message.conversation,
                "userid": userid,
            }
            # file messages are only added to history, not passing to llm
            if message.type == "file":
                history.add_message(message.to_lc())
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
                config={"metadata": chain_metadata},
            ):
                logger.trace(f"event: {event}")
                match event["event"]:
                    case "on_chain_start":
                        # There could be several chains, the most outer one is: event["name"] == "PybotAgentExecutor"
                        chain_run_id = event["run_id"]
                        if event["name"] == "PybotAgentExecutor":
                            history.add_message(message.to_lc())
                    case "on_chain_end":
                        # TODO: Once migrate to lcel there will be nasty chains, so I need to handle this properly.
                        # Only persist output on the inner chain, as there will be a duplication
                        # between the last inner chain invocation and the outer chain invocation
                        # I will lost the opportunity to persist the intermediate steps here, but
                        # I don't think it's important also I did not find a better solution for now.
                        if event["name"] != "PybotAgentExecutor":
                            msg = AIChatMessage(
                                parent_id=chain_run_id,
                                id=event["run_id"],
                                conversation=message.conversation,
                                # TODO: I think this can be improved on langchain side.
                                content=event["data"]["output"]["text"].removesuffix(
                                    "<|im_end|>"
                                ),
                            )
                            history.add_message(msg.to_lc())
                    case "on_chat_model_start":
                        logger.debug(f"event: {event}")
                        msg = AIChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            type="stream/start",
                        )
                        await websocket.send_text(msg.model_dump_json())
                    case "on_chat_model_stream":
                        # openai streaming provides eos token as last chunk, but langchain does not provide stop reason.
                        # It will be better if langchain could provide sth like event["data"]["chunk"].finish_reason == "eos_token"
                        if (content := event["data"]["chunk"].content) != "<|im_end|>":
                            msg = AIChatMessage(
                                parent_id=chain_run_id,
                                id=event["run_id"],
                                conversation=message.conversation,
                                content=content,
                                type="stream/text",
                            )
                            await websocket.send_text(msg.model_dump_json())
                    case "on_chat_model_end":
                        logger.debug(f"event: {event}")
                        msg = AIChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            type="stream/end",
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
                            additional_kwargs={
                                "prefix": f"<|im_start|>observation\n",
                                "suffix": "<|im_end|>",
                            },
                        )
                        await websocket.send_text(msg.model_dump_json())
                        history.add_message(msg.to_lc())
            conv.last_message_at = utcnow()
            await conv.save()
            # summarize if required
            if message.additional_kwargs and message.additional_kwargs.get(
                "require_summarization", False
            ):
                res = await smry_chain.ainvoke(
                    input={},
                    config={"metadata": chain_metadata},
                )
                title = res[smry_chain.output_key]
                conv.title = title
                await conv.save()
                info_message = InfoMessage(
                    conversation=message.conversation,
                    from_="system",
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
