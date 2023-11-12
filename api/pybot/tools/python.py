import time
from typing import Optional

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain.tools import BaseTool
from loguru import logger
from websockets.client import connect as aconnect
from websockets.sync.client import connect

from pybot.jupyter.schema import ExecutionRequest, ExecutionResponse


class CodeSandbox(BaseTool):
    name = "code_sandbox"
    description = "useful for when you need to execute code."
    channel_endpoint: str
    timeout: int = 60
    """The timeout for the tool in seconds."""

    def _run(
        self, code: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        payload = ExecutionRequest.of_code(code)
        logger.debug(f"kernel execution payload: {payload.model_dump_json()}")
        result = ""
        with connect(self.channel_endpoint) as websocket:
            websocket.send(payload.model_dump_json())
            timeout = time.time() + self.timeout
            while True:
                if time.time() > timeout:
                    result = f"Timeout after {self.timeout} seconds"
                    break
                message = websocket.recv()
                logger.trace(f"kernel execution message: [{message}]")
                response = ExecutionResponse.model_validate_json(message)
                match response.msg_type:
                    case "error":
                        result = f"{response.content.ename}: {response.content.evalue}"
                        break
                    case "execute_result":
                        result = response.content.data.text_plain
                        break
                    case "stream":
                        result = response.content.text
                        break
                    case _:
                        # debug because we don't handle many message types like status
                        logger.debug(f"Unhandled message type: {response.msg_type}")
        return result

    async def _arun(
        self, code: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool asynchronously."""
        payload = ExecutionRequest.of_code(code)
        logger.debug(f"kernel execution payload: {payload.model_dump_json()}")
        result = ""
        async with aconnect(self.channel_endpoint) as websocket:
            await websocket.send(payload.model_dump_json())
            timeout = time.time() + self.timeout
            while True:
                if time.time() > timeout:
                    result = f"Timeout after {self.timeout} seconds"
                    break
                message = await websocket.recv()
                logger.trace(f"kernel execution message: [{message}]")
                response = ExecutionResponse.model_validate_json(message)
                match response.msg_type:
                    case "error":
                        result = f"{response.content.ename}: {response.content.evalue}"
                        break
                    case "execute_result":
                        result = response.content.data.text_plain
                        break
                    case "stream":
                        result = response.content.text
                        break
                    case _:
                        # debug because we don't handle many message types like status
                        logger.debug(f"Unhandled message type: {response.msg_type}")
        return result
