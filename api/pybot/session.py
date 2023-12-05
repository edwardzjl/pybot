import asyncio
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from aredis_om import Field, JsonModel
from pydantic import BaseModel


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


class SessionStore(ABC):
    def get(self, id: str) -> Session:
        """Get a session by id"""
        return asyncio.run(self.aget(id))

    def save(self, session: Session) -> None:
        """Create a session"""
        return asyncio.run(self.save(session))

    def delete(self, id: str) -> None:
        """Delete a session"""
        return asyncio.run(self.delete(id))

    @abstractmethod
    async def aget(self, id: str) -> Session:
        """Get a session by id"""

    @abstractmethod
    async def asave(self, session: Session) -> None:
        """Create a session"""

    @abstractmethod
    async def adelete(self, id: str) -> None:
        """Delete a session"""


class RedisSessionStore(SessionStore, BaseModel):
    async def aget(self, id: str) -> Session:
        return await Session.get(id)

    async def asave(self, session: Session) -> None:
        await session.save()

    async def adelete(self, id: str) -> None:
        await Session.delete(id)
