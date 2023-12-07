from contextvars import ContextVar

from pybot.session import Session, SessionStore

session_id = ContextVar("session_id", default=None)  # principal:conv_id


class CurrentSession:
    def __init__(self, session_store: SessionStore):
        self.session_store = session_store

    def get(self) -> Session:
        return self.session_store.get(session_id.get())

    async def aget(self) -> Session:
        return await self.session_store.aget(session_id.get())
