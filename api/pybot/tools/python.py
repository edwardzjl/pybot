import asyncio
from typing import Any, Optional

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from loguru import logger
from pydantic.v1 import root_validator

from pybot.jupyter import ContextAwareKernelManager, ExecutionRequest, ExecutionResponse


class CodeSandbox(BaseTool):
    name = "python"
    timeout: int = 60
    """The timeout for the tool in seconds."""
    volume: str = "/mnt/shared"
    description = f"""A Python shell. Use this tool to execute python commands.
  - Action Input: Must be a valid python snippet
  - Reminder:
    - The driver at '{volume}' can be used to persist files.
    - {name} will respond with the output of the execution or time out after {timeout} seconds.
    - During data analysis with pandas, if you encounter missing columns, make sure to refer to `df.head()` for initial insights into the dataset.
  - Execution Environment: python3 with the following major dependencies:
    - pandas==1.5.3
    - scikit-learn
    - scikit-image
    - seaborn
    - matplotlib
    - SQLAlchemy
"""
    gateway_url: str
    kernel_manager: Optional[ContextAwareKernelManager] = None

    @root_validator(pre=True)
    def validate_environment(cls, values: dict[str, Any]) -> dict[str, Any]:
        values["kernel_manager"] = ContextAwareKernelManager(
            gateway_host=values["gateway_url"]
        )
        return values

    def _run(
        self, code: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        kernel = self.kernel_manager.start_kernel()
        with self.kernel_manager.upgrade(str(kernel.id)) as websocket:
            payload = ExecutionRequest.of_code(code)
            logger.debug(f"kernel execution payload: {payload.model_dump_json()}")
            result = ""
            try:
                websocket.send(payload.model_dump_json())
                while message := websocket.recv(timeout=self.timeout):
                    logger.trace(f"kernel execution message: [{message}]")
                    response = ExecutionResponse.model_validate_json(message)
                    match response.msg_type:
                        case "error":
                            result = (
                                f"{response.content.ename}: {response.content.evalue}"
                            )
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
            except Exception as e:
                logger.error(f"Something goes wrong, err: {str(e)}")
                result = str(e)
        return result

    async def _arun(
        self, code: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool asynchronously."""
        kernel = await self.kernel_manager.astart_kernel()
        async with self.kernel_manager.aupgrade(str(kernel.id)) as websocket:
            payload = ExecutionRequest.of_code(code)
            logger.debug(f"kernel execution payload: {payload.model_dump_json()}")
            result = ""
            try:
                await websocket.send(payload.model_dump_json())
                while message := await asyncio.wait_for(
                    websocket.recv(), timeout=self.timeout
                ):
                    logger.debug(f"kernel execution message: [{message}]")
                    response = ExecutionResponse.model_validate_json(message)
                    if response.parent_header.msg_id != payload.header.msg_id:
                        # ignore messages not related to this request
                        # should rarely happen, but in case there's some unprocessed messages from previous run
                        logger.debug(
                            f"Ignoring message of parent id {response.parent_header.msg_id} in request {payload.header.msg_id}"
                        )
                        continue
                    match response.msg_type:
                        case "error":
                            result = (
                                f"{response.content.ename}: {response.content.evalue}"
                            )
                        case "execute_result":
                            result = response.content.data.text_plain
                        case "stream":
                            result = response.content.text
                        case "status":
                            if response.content.execution_state == "idle":
                                # idle means the kernel has finished executing
                                # TODO: there will be rare situations that the idle message is received before the execute_result message
                                # See <https://github.com/jupyter-server/enterprise_gateway/blob/54c8e31d9b17418f35454b49db691d2ce5643c22/enterprise_gateway/client/gateway_client.py#L235C9-L235C9>
                                break
                        case _:
                            # debug because we don't handle many message types like status
                            logger.debug(f"Unhandled message type: {response.msg_type}")
            except Exception as e:
                logger.error(f"Something goes wrong, err: {str(e)}")
                result = str(e)
        return result
