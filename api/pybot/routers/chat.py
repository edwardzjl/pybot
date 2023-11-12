from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from langchain.chains import ConversationChain
from langchain.llms import BaseLLM
from langchain.memory import RedisChatMessageHistory
from loguru import logger

from pybot.callbacks import (
    StreamingLLMCallbackHandler,
    UpdateConversationCallbackHandler,
)
from pybot.memory import FlexConversationBufferWindowMemory
from pybot.prompts.vicuna import (
    ai_prefix,
    ai_suffix,
    human_prefix,
    human_suffix,
    prompt,
)
from pybot.routers.dependencies import get_llm, get_message_history
from pybot.schemas import ChatMessage
from pybot.utils import UserIdHeader

router = APIRouter(
    prefix="/api/chat",
    tags=["conversation"],
)


@router.websocket()
async def generate(
    websocket: WebSocket,
    llm: Annotated[BaseLLM, Depends(get_llm)],
    history: Annotated[RedisChatMessageHistory, Depends(get_message_history)],
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    await websocket.accept()
    memory = FlexConversationBufferWindowMemory(
        human_prefix=human_prefix,
        ai_prefix=ai_prefix,
        human_suffix=human_suffix,
        ai_suffix=ai_suffix,
        memory_key="history",
        chat_memory=history,
    )
    conversation_chain: ConversationChain = ConversationChain(
        llm=llm,
        prompt=prompt,
        verbose=False,
        memory=memory,
    )

    while True:
        try:
            payload: str = await websocket.receive_text()
            message = ChatMessage.model_validate_json(payload)
            history.session_id = f"{userid}:{message.conversation}"
            streaming_callback = StreamingLLMCallbackHandler(
                websocket, message.conversation
            )
            update_conversation_callback = UpdateConversationCallbackHandler(
                message.conversation
            )
            await conversation_chain.arun(
                message.content,
                callbacks=[streaming_callback, update_conversation_callback],
            )
        except WebSocketDisconnect:
            logger.info("websocket disconnected")
            return
        except Exception as e:
            logger.error(f"Something goes wrong, err: {e}")
