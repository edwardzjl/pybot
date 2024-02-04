from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
)
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.language_models import BaseLLM
from langchain_core.memory import BaseMemory
from loguru import logger

from pybot.agent.base import create_agent
from pybot.callbacks import (
    AgentActionCallbackHandler,
    StreamingLLMCallbackHandler,
    UpdateConversationCallbackHandler,
)
from pybot.config import settings
from pybot.context import session_id
from pybot.dependencies import ChatMemory, Llm, MessageHistory, UserIdHeader
from pybot.models import Conversation
from pybot.schemas import ChatMessage, InfoMessage
from pybot.summarization import summarize
from pybot.tools import CodeSandbox

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)


@router.websocket("")
@router.websocket("/")
async def chat(
    websocket: WebSocket,
    llm: Annotated[BaseLLM, Depends(Llm)],
    history: Annotated[RedisChatMessageHistory, Depends(MessageHistory)],
    memory: Annotated[BaseMemory, Depends(ChatMemory)],
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
            tools = [
                CodeSandbox(
                    gateway_url=str(settings.jupyter_enterprise_gateway_url),
                )
            ]
            agent_executor = create_agent(
                llm=llm,
                tools=tools,
                agent_executor_kwargs={
                    "memory": memory,
                    "return_intermediate_steps": True,
                },
            )
            streaming_callback = StreamingLLMCallbackHandler(
                websocket, message.conversation
            )
            update_conversation_callback = UpdateConversationCallbackHandler(
                message.conversation
            )
            action_callback = AgentActionCallbackHandler(
                websocket, message.conversation, history
            )
            await agent_executor.ainvoke(
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
                title = await summarize(llm, memory)
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
        except Exception as e:
            logger.error(f"Something goes wrong, err: {str(e)}")
