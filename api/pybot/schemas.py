from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from langchain.schema import BaseMessage
from pydantic import BaseModel, ConfigDict, Field, model_validator

from pybot.utils import utcnow


class File(BaseModel):
    id: Optional[str] = None
    filename: str
    path: str
    owner: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = created_at

    @model_validator(mode="before")
    @classmethod
    def set_id(cls, values):
        if "pk" in values and "id" not in values:
            values["id"] = values["pk"]
        return values

    def dump_minimal_json(self) -> str:
        return super().model_dump_json(include={"filename", "path"})


class ChatMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID = Field(default_factory=uuid4)
    """Message id, used to chain stream responses into message."""
    conversation: Optional[str] = None
    """Conversation id"""
    from_: Optional[str] = Field(None, alias="from")
    """A transient field to determine conversation id."""
    content: Optional[str | File] = None
    type: str
    # sent_at is not an important information for the user, as far as I can tell.
    # But it introduces some complexity in the code, so I'm removing it for now.
    # sent_at: datetime = Field(default_factory=datetime.now)

    @staticmethod
    def from_lc(
        lc_message: BaseMessage, conv_id: str, from_: str = None
    ) -> "ChatMessage":
        msg_id_str = lc_message.additional_kwargs.get("id", None)
        msg_id = UUID(msg_id_str) if msg_id_str else uuid4()
        msg_type = lc_message.additional_kwargs.get("type", "text")
        if msg_type == "file":
            msg_content = File.model_validate_json(lc_message.content)
        else:
            msg_content = lc_message.content
        return ChatMessage(
            id=msg_id,
            conversation=conv_id,
            from_=from_ if from_ else lc_message.type,
            content=msg_content,
            type=msg_type,
        )

    def model_dump(
        self, by_alias: bool = True, exclude_none: bool = True, **kwargs
    ) -> dict[str, Any]:
        return super().model_dump(
            by_alias=by_alias, exclude_none=exclude_none, **kwargs
        )

    def model_dump_json(
        self, by_alias: bool = True, exclude_none: bool = True, **kwargs
    ) -> str:
        return super().model_dump_json(
            by_alias=by_alias, exclude_none=exclude_none, **kwargs
        )


class Conversation(BaseModel):
    id: Optional[str] = None
    title: str
    owner: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = created_at

    @model_validator(mode="before")
    @classmethod
    def set_id(cls, values):
        if "pk" in values and "id" not in values:
            values["id"] = values["pk"]
        return values


class ConversationDetail(Conversation):
    """Conversation with messages."""

    messages: list[ChatMessage] = []


class UpdateConversation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
