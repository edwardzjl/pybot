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
from langchain_core.agents import AgentAction, AgentActionMessageLog
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
                        # There are several chains, the most outer one is name: TableGPTAgentExecutor
                        # We parse the final answer here.
                        if event["name"] == "PybotAgentExecutor":
                            output: str = event["data"]["output"]["output"]
                            # TODO: I think this can be improved on langchain side.
                            output = output.removesuffix("<|im_end|>")
                            msg = AIChatMessage(
                                parent_id=chain_run_id,
                                id=event["run_id"],
                                content=output,
                            )
                            await websocket.send_text(msg.model_dump_json())
                            history.add_message(msg.to_lc())
                    case "on_parser_end":
                        if not isinstance(event["data"]["output"], AgentAction):
                            continue
                        output = event["data"]["output"]
                        if not isinstance(output, AgentActionMessageLog):
                            raise RuntimeError()
                        msg = AIChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            content=output.log or "",
                            type="action",
                            additional_kwargs={
                                "action": {
                                    "tool": output.tool,
                                    "tool_input": output.tool_input,
                                },
                                # "prefix": f"<|im_start|>{event['name']}\n",
                                # "suffix": "<|im_end|>",
                            },
                        )
                        await websocket.send_text(msg.model_dump_json())
                        history.add_messages(output.message_log)
                    case "on_tool_end":
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="system",
                            content=event["data"]["output"],
                            type="observation",
                            additional_kwargs={
                                "tool": event["name"],
                                # "prefix": f"<|im_start|>observation\n",
                                # "suffix": "<|im_end|>",
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
        except Exception as e:
            logger.exception(f"Something goes wrong: {str(e)}")
