from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from langchain.llms import BaseLLM
from langchain.memory import RedisChatMessageHistory
from langchain.schema import HumanMessage
from loguru import logger

from pybot.agent.base import create_agent
from pybot.callbacks import (
    AgentActionCallbackHandler,
    StreamingLLMCallbackHandler,
    UpdateConversationCallbackHandler,
)
from pybot.config import settings
from pybot.memory import FlexConversationBufferWindowMemory
from pybot.models import Conversation
from pybot.prompts import AI_PREFIX, AI_SUFFIX, HUMAN_PREFIX, HUMAN_SUFFIX
from pybot.routers.dependencies import get_llm, get_message_history
from pybot.schemas import ChatMessage
from pybot.tools import CodeSandbox
from pybot.utils import UserIdHeader

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
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    await websocket.accept()
    memory = FlexConversationBufferWindowMemory(
        human_prefix=HUMAN_PREFIX,
        human_suffix=HUMAN_SUFFIX,
        ai_prefix=AI_PREFIX,
        ai_suffix=AI_SUFFIX,
        prefix_delimiter="\n",
        memory_key="history",
        input_key="input",
        output_key="output",
        chat_memory=history,
        return_messages=True,
    )
    while True:
        try:
            payload: str = await websocket.receive_text()
            message = ChatMessage.model_validate_json(payload)
            history.session_id = f"{userid}:{message.conversation}"
            # file messages are only added to history, not passing to llm
            if message.type == "file":
                lc_msg = HumanMessage(
                    content=message.content.model_dump_json(),
                    additional_kwargs={
                        "type": "file",
                    },
                )
                history.add_message(lc_msg)
                continue
            conv = await Conversation.get(message.conversation)
            tools = [
                CodeSandbox(
                    gateway_url=str(settings.jupyter_enterprise_gateway_url),
                    userid=userid,
                    kernel_id=str(conv.kernel_id),
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
