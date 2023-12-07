from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from langchain.llms import BaseLLM
from langchain.memory import RedisChatMessageHistory
from langchain.schema import BaseMemory
from loguru import logger

from pybot.agent.base import create_agent
from pybot.callbacks import (
    AgentActionCallbackHandler,
    StreamingLLMCallbackHandler,
    UpdateConversationCallbackHandler,
)
from pybot.config import settings
from pybot.context import session_id
from pybot.routers.dependencies import (
    UserIdHeader,
    get_llm,
    get_memory,
    get_message_history,
)
from pybot.schemas import ChatMessage
from pybot.tools import CodeSandbox

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)


@router.websocket("")
@router.websocket("/")
async def chat(
    websocket: WebSocket,
    llm: Annotated[BaseLLM, Depends(get_llm)],
    history: Annotated[RedisChatMessageHistory, Depends(get_message_history)],
    memory: Annotated[BaseMemory, Depends(get_memory)],
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    await websocket.accept()
    while True:
        try:
            payload: str = await websocket.receive_text()
            message = ChatMessage.model_validate_json(payload)
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
            await agent_executor.acall(
                inputs={
                    "date": date.today(),
                    "input": message.content,
                },
                callbacks=[
                    streaming_callback,
                    action_callback,
                    update_conversation_callback,
                ],
            )
        except WebSocketDisconnect:
            logger.info("websocket disconnected")
            return
        except Exception as e:
            logger.error(f"Something goes wrong, err: {str(e)}")
