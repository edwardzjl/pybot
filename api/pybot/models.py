from datetime import datetime
from typing import Optional
from uuid import UUID

from aredis_om import Field, JsonModel

from pybot.utils import utcnow


class Conversation(JsonModel):
    title: str
    owner: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = created_at
    kernel_id: Optional[UUID] = None
    """TODO: This is a transitent field, the kernel could be culled, I need to handle it elsewhere."""


class File(JsonModel):
    filename: str
    path: str
    conversation_id: str = Field(index=True)
    owner: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = created_at
