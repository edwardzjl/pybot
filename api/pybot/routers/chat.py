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

from pybot.callbacks import (
    AgentActionCallbackHandler,
    StreamingLLMCallbackHandler,
    UpdateConversationCallbackHandler,
)
from pybot.context import session_id
from pybot.dependencies import MessageHistory, PybotAgent, SmryChain, UserIdHeader
from pybot.models import Conversation
from pybot.schemas import ChatMessage, InfoMessage

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)


@router.websocket("")
@router.websocket("/")
async def chat(
    websocket: WebSocket,
    agent: Annotated[AgentExecutor, Depends(PybotAgent)],
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
            streaming_callback = StreamingLLMCallbackHandler(
                websocket, message.conversation
            )
            update_conversation_callback = UpdateConversationCallbackHandler(
                message.conversation
            )
            action_callback = AgentActionCallbackHandler(
                websocket, message.conversation, history
            )
            await agent.ainvoke(
                input={
                    "date": date.today(),
                    "input": message.content,
                },
                config={
                    "callbacks": [
                        streaming_callback,
                        action_callback,
                        update_conversation_callback,
                    ],
                },
                include_run_info=True,
            )
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
