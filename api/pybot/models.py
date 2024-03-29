from datetime import datetime

from aredis_om import Field, JsonModel

from pybot.utils import utcnow


class Conversation(JsonModel):
    title: str
    owner: str = Field(index=True)
    pinned: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    last_message_at: datetime = created_at

    class Meta:
        global_key_prefix = "pybot"


class File(JsonModel):
    """User uploaded files.
    I store this in db because LLM may manipulate the files and generate new ones,
    and it's not necessary for the user to be aware of these operations."""

    filename: str
    path: str
    """absolute path to file"""
    mounted_path: str
    """absolute path to file mounted in jupyter kernel"""
    size: int
    """size of file, in bytes"""
    conversation_id: str = Field(index=True)
    owner: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = created_at

    class Meta:
        global_key_prefix = "pybot"
