from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from langchain.chains.base import Chain
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
from pybot.dependencies import (
    ChatMemory,
    FakeCodeSandboxChain,
    Llm,
    MessageHistory,
    UserIdHeader,
)
from pybot.models import Conversation as ORMConversation
from pybot.schemas import ChatMessage, Conversation, InfoMessage
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
    preview_chain: Annotated[Chain, Depends(FakeCodeSandboxChain)],
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
                await preview_chain.acall(inputs={"input": message})
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
            # summarize if required
            if (
                message.additional_kwargs
                and "require_summarization" in message.additional_kwargs
                and message.additional_kwargs["require_summarization"]
            ):
                title = await summarize(llm, memory)
                conv = await ORMConversation.get(message.conversation)
                conv.title = title
                await conv.save()
                info_message = InfoMessage(
                    conversation=message.conversation,
                    from_="ai",
                    content={
                        "type": "update_conv",
                        "payload": Conversation(**conv.dict()).model_dump(),
                    },
                )
                await websocket.send_text(info_message.model_dump_json())
        except WebSocketDisconnect:
            logger.info("websocket disconnected")
            return
        except Exception as e:
            logger.error(f"Something goes wrong, err: {str(e)}")
