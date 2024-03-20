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
        payload = ExecutionRequest.of_code(code)
        logger.debug(f"kernel execution payload: {payload.model_dump_json()}")
        kernel = self.kernel_manager.start_kernel()
        with self.kernel_manager.upgrade(str(kernel.id)) as websocket:
            result = ""
            try:
                websocket.send(payload.model_dump_json())
                while message := websocket.recv(timeout=self.timeout):
                    logger.trace(f"kernel execution message: [{message}]")
                    response = ExecutionResponse.model_validate_json(message)
                    if response.parent_header.msg_id != payload.header.msg_id:
                        # This message does not belong to the current execution
                        # As we break early once we get the result, this could happen
                        logger.debug(
                            f"Ignoring message of parent id {response.parent_header.msg_id} in request {payload.header.msg_id}"
                        )
                        continue
                    match response.msg_type:
                        case "execute_input":
                            # Ignore broadcast message
                            # See <https://jupyter-client.readthedocs.io/en/latest/messaging.html#code-inputs>
                            logger.trace("Ignoring broadcast execution input.")
                        case "execute_reply":
                            # See <https://jupyter-client.readthedocs.io/en/latest/messaging.html#execution-results>
                            # error execution may have extra messages, for example a stream std error
                            if response.content.status == "error":
                                result = f"{response.content.ename}: {response.content.evalue}"
                            # For status != "error" we may want to extract the result from "stream" or "execute_result"
                        case "execute_result":
                            # See <https://jupyter-client.readthedocs.io/en/latest/messaging.html#id6>
                            result = response.content.data.text_plain
                        case "display_data":
                            # TODO: We can persist images here and return the path
                            # See <https://jupyter-client.readthedocs.io/en/latest/messaging.html#display-data>
                            ...
                        case "stream":
                            # 'stream' is treated as second-class citizen. If 'execute_result', 'display_data' or 'execute_reply.error' exists,
                            # We ignore the 'stream' message. If only all other messages has nothing to display, we will use the 'stream' message.
                            if not result:
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

    async def _arun(
        self, code: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool asynchronously."""
        payload = ExecutionRequest.of_code(code)
        logger.debug(f"kernel execution payload: {payload.model_dump_json()}")
        kernel = await self.kernel_manager.astart_kernel()
        async with self.kernel_manager.aupgrade(str(kernel.id)) as websocket:
            result = ""
            try:
                await websocket.send(payload.model_dump_json())
                while message := await asyncio.wait_for(
                    websocket.recv(), timeout=self.timeout
                ):
                    logger.trace(f"kernel execution message: [{message}]")
                    response = ExecutionResponse.model_validate_json(message)
                    if response.parent_header.msg_id != payload.header.msg_id:
                        # This message does not belong to the current execution
                        # As we break early once we get the result, this could happen
                        logger.debug(
                            f"Ignoring message of parent id {response.parent_header.msg_id} in request {payload.header.msg_id}"
                        )
                        continue
                    match response.msg_type:
                        case "execute_input":
                            # Ignore broadcast message
                            # See <https://jupyter-client.readthedocs.io/en/latest/messaging.html#code-inputs>
                            logger.trace("Ignoring broadcast execution input.")
                        case "execute_reply":
                            # See <https://jupyter-client.readthedocs.io/en/latest/messaging.html#execution-results>
                            # error execution may have extra messages, for example a stream std error
                            if response.content.status == "error":
                                result = f"{response.content.ename}: {response.content.evalue}"
                            # For status != "error" we may want to extract the result from "stream" or "execute_result"
                        case "execute_result":
                            # See <https://jupyter-client.readthedocs.io/en/latest/messaging.html#id6>
                            result = response.content.data.text_plain
                        case "display_data":
                            # TODO: We can persist images here and return the path
                            # See <https://jupyter-client.readthedocs.io/en/latest/messaging.html#display-data>
                            ...
                        case "stream":
                            # 'stream' is treated as second-class citizen. If 'execute_result', 'display_data' or 'execute_reply.error' exists,
                            # We ignore the 'stream' message. If only all other messages has nothing to display, we will use the 'stream' message.
                            if not result:
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
