from datetime import datetime
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, UploadFile

from pybot.config import settings
from pybot.models import File as ORMFile
from pybot.routers.dependencies import UserIdHeader
from pybot.schemas import File

router = APIRouter(
    prefix="/api/conversations/{conversation_id}/files",
    tags=["files"],
)


@router.post("", status_code=201)
async def upload_files(
    conversation_id: str,
    files: list[UploadFile],
    userid: Annotated[str | None, UserIdHeader()] = None,
) -> list[File]:
    base = Path(settings.shared_volume)
    parent_dir = base.joinpath(userid).joinpath(conversation_id)
    parent_dir.mkdir(exist_ok=True, parents=True)
    res = []
    for file in files:
        filename = file.filename
        file_path = parent_dir.joinpath(filename)
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
        await f.save()
        res.append(File.model_validate(f.dict()))
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
    return [File.model_validate(file.dict()) for file in files]
