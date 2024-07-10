import asyncio
from contextvars import ContextVar
from typing import Optional
from uuid import UUID

from aredis_om import Field, JsonModel

session_id = ContextVar("session_id", default=None)  # principal:conv_id


class Session(JsonModel):
    """Session stores states of requests."""

    user_id: str = Field(index=True)
    """The user id of the owner of the session."""
    conv_id: Optional[str] = None
    kernel_id: Optional[UUID] = None
    """Last activate kernel id of the session.
    When it expires (culled by the gateway), I need to start a new kernel and update this field."""

    class Meta:
        global_key_prefix = "pybot"


class CurrentSession:
    def get(self) -> Session:
        return asyncio.run(Session.get(session_id.get()))

    async def aget(self) -> Session:
        return await Session.get(session_id.get())
