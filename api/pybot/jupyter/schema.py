from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CreateKernelRequest(BaseModel):
    name: Optional[str] = None
    """Kernel spec name (defaults to default kernel spec for server)."""
    env: Optional[dict[str, str]] = None
    """A dictionary of environment variables and values to include in the kernel process - subject to filtering."""


class CreateKernelResponse(BaseModel):
    id: UUID
    name: str
    last_activity: datetime
    execution_state: str
    """idk if it belongs to {'starting', 'idle', 'busy', 'restarting', 'dead'}"""
    connections: int


def uuid4_hex() -> str:
    return uuid4().hex


class ExecutionHeader(BaseModel):
    msg_id: str = Field(default_factory=uuid4_hex)
    """msg_id in response is not a UUID."""
    msg_type: str = Field(default="execute_request")
    """I see 'execute_request', 'execute_input', 'execute_reply', 'stream' and 'status', don't know if there's more."""
    username: Optional[str] = None
    """When set to None, the response will generate a fake 'username'."""
    session: Optional[str] = None
    """Optional in request."""
    date: Optional[datetime] = None
    """Optional in request."""
    version: Optional[str] = None
    """Optional in request."""


class ExecutionContent(BaseModel):
    code: str
    silent: bool = False
    store_history: bool = False
    user_expressions: dict = {}
    allow_stdin: bool = False


class ExecutionRequest(BaseModel):
    header: ExecutionHeader
    parent_header: dict = {}
    """IDK what this is for but if I don't include it, the kernel will disconnect."""
    metadata: dict = {}
    """IDK what this is for but if I don't include it, the kernel will disconnect."""
    content: ExecutionContent
    buffers: list = None
    """This seems optional."""
    channel: str = "shell"
    """I see there's 'iopub' and 'shell', don't know if there's more."""

    def model_dump(self):
        return super().model_dump(by_alias=True, exclude_none=True)

    def model_dump_json(self):
        return super().model_dump_json(by_alias=True, exclude_none=True)


class ExecutionStatusContent(BaseModel):
    execution_state: str
    """I see 'busy' and 'idle', don't know if there's more."""


class ExecutionReplyContent(BaseModel):
    status: str
    """I see 'ok' and 'error', don't know if there's more."""
    execution_count: int
    user_expressions: dict
    payload: list
    # Following are only available when status == 'error', and seems duplicated. Maybe I should just ignore extra fields.
    traceback: Optional[list[str]] = None
    ename: Optional[str] = None
    evalue: Optional[str] = None
    engine_info: Optional[dict] = None


class ExecutionInputContent(BaseModel):
    code: str
    execution_count: int


class StreamContent(BaseModel):
    name: str
    """I see 'stdout', don't know if there's more."""
    text: str


class ErrorContent(BaseModel):
    ename: str
    evalue: str
    traceback: list[str]


class ExecutionResultData(BaseModel):
    text_plain: str = Field(alias="text/plain")


class ExecutionResultContent(BaseModel):
    data: ExecutionResultData
    metadata: dict
    execution_count: int


class ExecutionResponse(BaseModel):
    header: ExecutionHeader
    msg_id: str
    """Identical to header.msg_id."""
    msg_type: str
    """I see 'execute_request', 'execute_input', 'execute_reply', 'stream' and 'status', don't know if there's more.
    Identical to header.msg_type."""
    parent_header: ExecutionHeader
    metadata: dict
    content: ExecutionStatusContent | ExecutionReplyContent | ExecutionInputContent | StreamContent | ErrorContent | ExecutionResultContent
    buffers: list
    channel: str
    """I see there's 'iopub' and 'shell', don't know if there's more."""
