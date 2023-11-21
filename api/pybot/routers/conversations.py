from typing import Annotated

from fastapi import APIRouter, Depends
from langchain.memory import RedisChatMessageHistory
from loguru import logger

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
    history.session_id = f"{userid}:{conversation_id}"
    return ConversationDetail(
        messages=[
            ChatMessage.from_lc(
                lc_message=message, conv_id=conversation_id, from_=userid
            )
            if message.type == "user"
            else ChatMessage.from_lc(lc_message=message, conv_id=conversation_id)
            for message in history.messages
        ],
        **conv.dict(),
    )


@router.post("", status_code=201)
async def create_conversation(
    userid: Annotated[str | None, UserIdHeader()] = None
) -> ConversationDetail:
    # using the same path of shared volume on chat app and jupyter kernels will ease the maintainence
    env = {
        "KERNEL_USERNAME": userid,
        "KERNEL_VOLUME_MOUNTS": [
            {"name": "shared-vol", "mountPath": settings.shared_volume}
        ],
        "KERNEL_VOLUMES": [
            {
                "name": "shared-vol",
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
) -> None:
    conv = await ORMConversation.get(conversation_id)
    conv.title = payload.title
    await conv.save()


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> None:
    conv = await ORMConversation.get(conversation_id)
    try:
        gateway_client.delete_kernel(conv.kernel_id)
    except Exception as e:
        logger.exception(f"failed to delete kernel {conv.kernel_id}, err: {str(e)}")
    await ORMConversation.delete(conversation_id)
