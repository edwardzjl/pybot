from typing import Annotated

from fastapi import APIRouter, Depends
from langchain.memory import RedisChatMessageHistory

from pybot.config import settings
from pybot.jupyter import CreateKernelRequest, GatewayClient
from pybot.models import Conversation as ORMConversation
from pybot.routers.dependencies import get_message_history
from pybot.schemas import (
    ChatMessage,
    Conversation,
    ConversationDetail,
    UpdateConversation,
)
from pybot.utils import UserIdHeader

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversation"],
)
gateway_client = GatewayClient(host=settings.jupyter_enterprise_gateway_url)


@router.get("", response_model=list[Conversation])
async def get_conversations(userid: Annotated[str | None, UserIdHeader()] = None):
    convs = await ORMConversation.find(ORMConversation.owner == userid).all()
    convs.sort(key=lambda x: x.updated_at, reverse=True)
    return [Conversation(**conv.dict()) for conv in convs]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    history: Annotated[RedisChatMessageHistory, Depends(get_message_history)],
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    conv = await ORMConversation.get(conversation_id)
    history.session_id = f"{userid}:{conversation_id}"
    return ConversationDetail(
        messages=[
            ChatMessage.from_lc(lc_message=message, conv_id=conversation_id, from_="ai")
            if message.type == "ai"
            else ChatMessage.from_lc(
                lc_message=message, conv_id=conversation_id, from_=userid
            )
            for message in history.messages
        ],
        **conv.dict(),
    )


@router.post("", status_code=201, response_model=ConversationDetail)
async def create_conversation(userid: Annotated[str | None, UserIdHeader()] = None):
    env = {
        "KERNEL_USERNAME": userid,
        "KERNEL_VOLUME_MOUNTS": [{"name": "nfs-volume", "mountPath": "/mnt/data"}],
        "KERNEL_VOLUMES": [
            {
                "name": "nfs-volume",
                "nfs": {"server": settings.nfs_server, "path": settings.nfs_path},
            }
        ],
    }
    if settings.kernel_namespace:
        env["KERNEL_NAMESPACE"] = settings.kernel_namespace
    request = CreateKernelRequest(env=env)
    response = gateway_client.create_kernel(request)
    conv = ORMConversation(title=f"New chat", owner=userid, kernel_id=response.id)
    await conv.save()
    return ConversationDetail(**conv.dict())


@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversation,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    conv = await ORMConversation.get(conversation_id)
    conv.title = payload.title
    await conv.save()


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    conv = await ORMConversation.get(conversation_id)
    gateway_client.delete_kernel(conv.kernel_id)
    await ORMConversation.delete(conversation_id)
