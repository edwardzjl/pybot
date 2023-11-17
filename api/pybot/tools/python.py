import asyncio
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
from pybot.tools.base import ExtendedTool


class CodeSandbox(ExtendedTool):
    name = "code_sandbox"
    timeout: int = 60
    """The timeout for the tool in seconds."""
    description = f"""
- {name}:
  - Description: {name} is a powerful tool designed for executing Python code, facilitating diverse tasks such as like data analysis, data visualization, etc.
  - Execution Environment: python3 Jupyter notebook with the following major dependencies:
    - pandas==1.5.3
    - scikit-learn
    - scikit-image
    - seaborn
    - SQLAlchemy
  - Usage Schema: When involking {name}, ensure that you provide a JSON object adhering to the following schema:

    ```yaml
    ToolRequest:
    type: object
    properties:
        tool_name:
        type: string
        enum: ["{name}"]
        tool_input:
        type: string
        description: the code you want {name} to execute
    required: [tool_name, tool_input]
    ```
"""
    examples: str = """<|im_start|>system example-user
{"filename":"test.csv","path":"/mnt/data/test.csv"}<|im_end|>
<|im_start|>system example-user
how many rows are there?<|im_end|>
<|im_start|>system example-assistant
To count the rows of the file I will use the code_sandbox tool. Given that the file is in CSV format, I will use the pandas library to read the file and count the rows.
```json
{
    "tool_name": "code_sandbox",
    "tool_input": "import pandas as pd\\n\\n# read the file\\ndf = pd.read_csv(\'test.csv\')\\n\\n# count the rows\\nlen(df)"
}
```<|im_end|>"""
    channel_endpoint: str

    def _run(
        self, code: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        payload = ExecutionRequest.of_code(code)
        logger.debug(f"kernel execution payload: {payload.model_dump_json()}")
        result = ""
        with connect(self.channel_endpoint) as websocket:
            try:
                websocket.send(payload.model_dump_json())
                while True:
                    message = websocket.recv(timeout=self.timeout)
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
        payload = ExecutionRequest.of_code(code)
        logger.debug(f"kernel execution payload: {payload.model_dump_json()}")
        result = ""
        async with aconnect(self.channel_endpoint) as websocket:
            try:
                await websocket.send(payload.model_dump_json())
                while True:
                    message = await asyncio.wait_for(
                        websocket.recv(), timeout=self.timeout
                    )
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
