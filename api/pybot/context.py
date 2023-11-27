from contextvars import ContextVar

session_id = ContextVar("session_id", default=None)  # principal:conv_id
principal = ContextVar("principal", default=None)  # aka user_id
conv_id = ContextVar("conv_id", default=None)
