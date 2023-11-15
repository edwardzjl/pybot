import os
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, UploadFile

from pybot.config import settings
from pybot.models import File as ORMFile
from pybot.schemas import File
from pybot.utils import UserIdHeader

router = APIRouter(
    prefix="/api/conversations/{conversation_id}/files",
    tags=["files"],
)


@router.post("")
async def upload_files(
    conversation_id: str,
    files: list[UploadFile],
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> list[File]:
    parent_dir = Path(
        os.path.join(str(settings.shared_volume), userid, conversation_id)
    )
    parent_dir.mkdir(exist_ok=True, parents=True)
    res = []
    for file in files:
        file_path = os.path.join(parent_dir, file.filename)
        async with aiofiles.open(file_path, "wb") as out_file:
            while content := await file.read(1024):
                await out_file.write(content)
        f = ORMFile(
            filename=file.filename,
            path=file_path,
            owner=userid,
            conversation_id=conversation_id,
        )
        await f.save()
        res.append(File(**f.dict()))
    return res


@router.get("")
async def get_files(
    conversation_id: str,
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> list[File]:
    files = await ORMFile.find(
        (ORMFile.owner == userid) & (ORMFile.conversation_id == conversation_id)
    ).all()
    files.sort(key=lambda x: x.filename)
    return [File(**file.dict()) for file in files]
