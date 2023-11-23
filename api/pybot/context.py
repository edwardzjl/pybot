from contextvars import ContextVar

session_id = ContextVar("session_id", default=None)  # principal:conv_id
principal = ContextVar("principal", default=None)
conv_id = ContextVar("conv_id", default=None)
