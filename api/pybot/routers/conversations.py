from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from langchain.chains.base import Chain
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import HumanMessage
from loguru import logger

from pybot.config import settings
from pybot.context import Session, session_id
from pybot.dependencies import MessageHistory, SmryChain, UserIdHeader
from pybot.jupyter import ContextAwareKernelManager, GatewayClient
from pybot.models import Conversation as ORMConversation
from pybot.schemas import (
    ChatMessage,
    Conversation,
    ConversationDetail,
    CreateConversation,
    UpdateConversation,
)

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversation"],
)
gateway_client = GatewayClient(host=settings.jupyter_enterprise_gateway_url)
kernel_manager = ContextAwareKernelManager(
    gateway_host=settings.jupyter_enterprise_gateway_url
)


@router.get("")
async def get_conversations(
    userid: Annotated[str | None, UserIdHeader()] = None
) -> list[Conversation]:
    convs = await ORMConversation.find(ORMConversation.owner == userid).all()
    convs.sort(key=lambda x: (x.pinned, x.updated_at), reverse=True)
    return [Conversation(**conv.dict()) for conv in convs]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    history: Annotated[RedisChatMessageHistory, Depends(MessageHistory)],
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> ConversationDetail:
    conv = await ORMConversation.get(conversation_id)
    if conv.owner != userid:
        raise HTTPException(status_code=403, detail="authorization error")
    session_id.set(f"{userid}:{conversation_id}")
    return ConversationDetail(
        messages=[
            (
                ChatMessage.from_lc(
                    lc_message=message, conv_id=conversation_id, from_=userid
                )
                if isinstance(message, HumanMessage)
                else ChatMessage.from_lc(lc_message=message, conv_id=conversation_id)
            )
            for message in history.messages
        ],
        **conv.dict(),
    )


@router.post("", status_code=201)
async def create_conversation(
    payload: CreateConversation, userid: Annotated[str | None, UserIdHeader()] = None
) -> ConversationDetail:
    conv = ORMConversation(title=payload.title, owner=userid)
    await conv.save()
    # create session
    session = Session(pk=f"{userid}:{conv.pk}", user_id=userid, conv_id=conv.pk)
    await session.save()
    session_id.set(session.pk)
    await kernel_manager.astart_kernel()
    return ConversationDetail(**conv.dict())


@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversation,
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> ConversationDetail:
    conv = await ORMConversation.get(conversation_id)
    if conv.owner != userid:
        raise HTTPException(status_code=403, detail="authorization error")
    modified = False
    if payload.title is not None:
        conv.title = payload.title
        modified = True
    if payload.pinned is not None:
        conv.pinned = payload.pinned
        modified = True
    if modified:
        await conv.save()
    return ConversationDetail(**conv.dict())


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> None:
    conv = await ORMConversation.get(conversation_id)
    if conv.owner != userid:
        raise HTTPException(status_code=403, detail="authorization error")
    try:
        session = await Session.get(f"{userid}:{conversation_id}")
        # delete kernel
        gateway_client.delete_kernel(str(session.kernel_id))
        # delete session
        await Session.delete(f"{userid}:{conversation_id}")
    except Exception as e:
        logger.exception(f"failed to delete session, err: {str(e)}")
    # delete conversation
    await ORMConversation.delete(conversation_id)


@router.post("/{conversation_id}/summarization", status_code=201)
async def summarize(
    conversation_id: str,
    smry_chain: Annotated[Chain, Depends(SmryChain)],
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> dict[str, str]:
    conv = await ORMConversation.get(conversation_id)
    if conv.owner != userid:
        raise HTTPException(status_code=403, detail="authorization error")
    session_id.set(f"{userid}:{conversation_id}")
    res = await smry_chain.ainvoke(input={})
    title = res[smry_chain.output_key]
    conv.title = title
    await conv.save()
    return {"title": title}
