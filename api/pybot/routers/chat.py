from datetime import date
from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from langchain_core.agents import AgentAction, AgentActionMessageLog
from loguru import logger

from pybot.config import settings
from pybot.context import session_id
from pybot.dependencies import UserIdHeader, agent_executor, history, smry_chain
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
            chain_run_id = None
            async for event in agent_executor.astream_events(
                input={
                    "input": message.content,
                    # create a new date on every message to solve message across days.
                    "date": date.today(),
                },
                include_run_info=True,
                version="v1",
                config={"metadata": chain_metadata},
            ):
                event_name: str = event["name"]
                if event_name.startswith("_"):
                    # langchain's internal event, for example '_Exception'
                    # skip for mainly 2 reasons:
                    # 1. we don't want to expose internal event to the user (websocket or history)
                    # 2. we want to keep the conversation history as short as possible
                    logger.debug(f"skipping internal event: {event_name}")
                    continue
                logger.trace(f"event: {event}")
                match event["event"]:
                    case "on_chain_start":
                        # There could be several chains, the most outer one is: event_name == "PybotAgentExecutor"
                        chain_run_id = event["run_id"]
                        if event_name == "PybotAgentExecutor":
                            history.add_message(message.to_lc())
                    case "on_chain_end":
                        # There are several chains, the most outer one is name: TableGPTAgentExecutor
                        # We parse the final answer here.
                        if event_name == "PybotAgentExecutor":
                            msg = AIChatMessage(
                                parent_id=chain_run_id,
                                id=event["run_id"],
                                content=event["data"]["output"]["output"].strip(),
                            )
                            await websocket.send_text(msg.model_dump_json())
                            history.add_message(msg.to_lc())
                    case "on_parser_end":
                        if not isinstance(event["data"]["output"], AgentAction):
                            continue
                        output = event["data"]["output"]
                        if not isinstance(output, AgentActionMessageLog):
                            raise RuntimeError()
                        # caveats: message_log from output parser lack some information, so we need to add them manually
                        msgs = output.message_log
                        for msg in msgs:
                            msg.additional_kwargs = msg.additional_kwargs | {
                                "parent_id": chain_run_id,
                                "id": event["run_id"],
                                "type": "action",
                            }
                            _msg = ChatMessage.from_lc(msg)
                            await websocket.send_text(_msg.model_dump_json())
                        await history.aadd_messages(msgs)
                    case "on_tool_end":
                        msg = ChatMessage(
                            parent_id=chain_run_id,
                            id=event["run_id"],
                            conversation=message.conversation,
                            from_="system",
                            content=event["data"]["output"],
                            type="observation",
                            additional_kwargs={
                                "tool": event_name,
                            },
                        )
                        await websocket.send_text(msg.model_dump_json())
                        history.add_message(msg.to_lc())
                    # Following are for local development logging.
                    # For production we may use something like [lunary](https://github.com/lunary-ai/lunary)
                    case "on_chat_model_end":
                        logger.debug(f"on_chat_model_end event: {event}")
                    case "on_llm_end":
                        logger.debug(f"on_llm_end event: {event}")
            conv.last_message_at = utcnow()
            await conv.save()
            # summarize if required
            if message.additional_kwargs and message.additional_kwargs.get(
                "require_summarization", False
            ):
                title_raw: str = await smry_chain.ainvoke(
                    input={},
                    config={"metadata": chain_metadata},
                )
                title = title_raw.strip('"')
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
