from typing import Annotated

from fastapi import APIRouter, Depends
from langchain.memory import RedisChatMessageHistory
from langchain.schema import HumanMessage
from loguru import logger

from pybot.config import settings
from pybot.context import session_id
from pybot.jupyter import ContextAwareKernelManager, GatewayClient
from pybot.models import Conversation as ORMConversation
from pybot.routers.dependencies import UserIdHeader, get_message_history
from pybot.schemas import (
    ChatMessage,
    Conversation,
    ConversationDetail,
    UpdateConversation,
)
from pybot.session import RedisSessionStore, Session

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversation"],
)
gateway_client = GatewayClient(host=settings.jupyter_enterprise_gateway_url)
session_store = RedisSessionStore()
kernel_manager = ContextAwareKernelManager(
    gateway_host=settings.jupyter_enterprise_gateway_url
)


@router.get("")
async def get_conversations(
    userid: Annotated[str | None, UserIdHeader()] = None
) -> list[Conversation]:
    convs = await ORMConversation.find(ORMConversation.owner == userid).all()
    convs.sort(key=lambda x: x.updated_at, reverse=True)
    return [Conversation(**conv.dict()) for conv in convs]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    history: Annotated[RedisChatMessageHistory, Depends(get_message_history)],
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> ConversationDetail:
    conv = await ORMConversation.get(conversation_id)
    session_id.set(f"{userid}:{conversation_id}")
    return ConversationDetail(
        messages=[
            ChatMessage.from_lc(
                lc_message=message, conv_id=conversation_id, from_=userid
            )
            if isinstance(message, HumanMessage)
            else ChatMessage.from_lc(lc_message=message, conv_id=conversation_id)
            for message in history.messages
        ],
        **conv.dict(),
    )


@router.post("", status_code=201)
async def create_conversation(
    userid: Annotated[str | None, UserIdHeader()] = None
) -> ConversationDetail:
    conv = ORMConversation(title=f"New chat", owner=userid)
    await conv.save()
    # create session
    session = Session(pk=f"{userid}:{conv.pk}", user_id=userid)
    await session_store.asave(session)
    session_id.set(session.pk)
    await kernel_manager.astart_kernel()
    return ConversationDetail(**conv.dict())


@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversation,
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> None:
    conv = await ORMConversation.get(conversation_id)
    conv.title = payload.title
    await conv.save()


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> None:
    session = await session_store.aget(f"{userid}:{conversation_id}")
    # delete kernel
    try:
        gateway_client.delete_kernel(str(session.kernel_id))
    except Exception as e:
        logger.exception(f"failed to delete kernel {session.kernel_id}, err: {str(e)}")
    # delete session
    await session_store.adelete(f"{userid}:{conversation_id}")
    # delete conversation
    await ORMConversation.delete(conversation_id)
