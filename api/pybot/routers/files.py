from datetime import datetime
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from langchain_core.chat_history import BaseChatMessageHistory

from pybot.config import settings
from pybot.context import session_id
from pybot.dependencies import UserIdHeader, history
from pybot.models import Conversation as ORMConversation
from pybot.models import File as ORMFile
from pybot.schemas import ChatMessage, File

router = APIRouter(
    prefix="/api/conversations/{conversation_id}/files",
    tags=["files"],
)


@router.post("", status_code=201)
async def upload_files(
    conversation_id: str,
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> list[File]:
    conv = await ORMConversation.get(conversation_id)
    if conv.owner != userid:
        raise HTTPException(status_code=403, detail="authorization error")
    base = Path(settings.jupyter.shared_volume_mount_path)
    parent_dir = base.joinpath(userid).joinpath(conversation_id)
    # This should never happen, as the 'userid' and 'conversation_id' are controlled by us.
    # But there's a code QL warning about it.
    if not base in parent_dir.absolute().parents:
        raise HTTPException(status_code=500, detail="invalid file path")
    parent_dir.mkdir(exist_ok=True, parents=True)
    ofiles: list[ORMFile] = []
    for file in files:
        filename = file.filename
        file_path = parent_dir.joinpath(filename)
        # To prevent user upload malformatted file path
        if parent_dir != file_path.absolute().parent:
            raise HTTPException(status_code=403, detail="invalid file path")
        if file_path.is_file():
            suffix = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            filename = f"{file_path.stem}_{suffix}{file_path.suffix}"
            file_path = parent_dir.joinpath(filename)

        async with aiofiles.open(file_path, "wb") as out_file:
            while content := await file.read(1024):
                await out_file.write(content)
        f = ORMFile(
            filename=filename,
            path=file_path.absolute().as_posix(),
            mounted_path=base.joinpath(filename).absolute().as_posix(),
            size=file.size,
            owner=userid,
            conversation_id=conversation_id,
        )
        ofiles.append(f)
        await f.save()
    background_tasks.add_task(
        add_file_messages, ofiles, history, f"{userid}:{conversation_id}"
    )
    return [File.model_validate(f.dict()) for f in ofiles]


def add_file_messages(ofiles: ORMFile, history: BaseChatMessageHistory, sid: str):
    session_id.set(sid)
    msgs = [
        ChatMessage(
            from_="human",
            type="file",
            content=File.model_validate(ofile.dict()),
        )
        for ofile in ofiles
    ]
    history.add_messages([msg.to_lc() for msg in msgs])


@router.get("")
async def get_files(
    conversation_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> list[File]:
    files = await ORMFile.find(
        (ORMFile.owner == userid) & (ORMFile.conversation_id == conversation_id)
    ).all()
    files.sort(key=lambda x: x.filename)
    return [File.model_validate(file.dict()) for file in files]
