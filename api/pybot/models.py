from datetime import datetime

from aredis_om import Field, JsonModel

from pybot.utils import utcnow


class Conversation(JsonModel):
    title: str
    owner: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = created_at

    class Meta:
        global_key_prefix = "pybot"


class File(JsonModel):
    filename: str
    path: str
    conversation_id: str = Field(index=True)
    owner: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = created_at

    class Meta:
        global_key_prefix = "pybot"
