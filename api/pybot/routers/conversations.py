import os
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, UploadFile
from langchain.memory import RedisChatMessageHistory

from pybot.config import settings
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


@router.get("/conversations", response_model=list[Conversation])
async def get_conversations(userid: Annotated[str | None, UserIdHeader()] = None):
    convs = await ORMConversation.find(ORMConversation.owner == userid).all()
    convs.sort(key=lambda x: x.updated_at, reverse=True)
    return [Conversation(**conv.dict()) for conv in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
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


@router.post("/conversations", status_code=201, response_model=ConversationDetail)
async def create_conversation(userid: Annotated[str | None, UserIdHeader()] = None):
    conv = ORMConversation(title=f"New chat", owner=userid)
    await conv.save()
    return ConversationDetail(**conv.dict())


@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversation,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    conv = await ORMConversation.get(conversation_id)
    conv.title = payload.title
    await conv.save()


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    await ORMConversation.delete(conversation_id)


@router.post("/conversations/{conversation_id}/files")
async def upload_files(
    conversation_id: str,
    files: list[UploadFile],
    userid: Annotated[str | None, UserIdHeader()] = None,
):
    parent_dir = Path(
        os.path.join(str(settings.shared_volume), userid, conversation_id)
    )
    parent_dir.mkdir(exist_ok=True, parents=True)
    for file in files:
        file_path = os.path.join(parent_dir, file.filename)
        async with aiofiles.open(file_path, "wb") as out_file:
            while content := await file.read(1024):
                await out_file.write(content)
    return {"filenames": [file.filename for file in files]}
