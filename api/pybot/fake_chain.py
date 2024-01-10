import os
from typing import Any, Dict, List, Optional

from langchain.callbacks.manager import (
    AsyncCallbackManagerForChainRun,
    CallbackManagerForChainRun,
)
from langchain.chains.base import Chain
from langchain.memory.chat_memory import BaseChatMemory
from langchain_core.agents import AgentAction

from pybot.agent.output_parser import JsonOutputParser
from pybot.config import settings
from pybot.jupyter.kernel import ContextAwareKernelManager
from pybot.schemas import ChatMessage, File
from pybot.tools import CodeSandbox

kernel_manager = ContextAwareKernelManager(
    gateway_host=settings.jupyter_enterprise_gateway_url
)

system = """The user just uploaded a dataset:{file_path}, and here's the initial step I did for you:"""

code_template = """
```json
{{
    "tool_name": "code_sandbox",
    "tool_input": "import pandas as pd\\n\\ndef read_data(file_path):\\n    # Get file extension\\n    file_extension = file_path.split(\'.\')[-1].lower()\\n\\n    if file_extension == \'csv\':\\n        df = pd.read_csv(file_path)\\n    elif file_extension in [\'xls\', \'xlsx\']:\\n        df = pd.read_excel(file_path)\\n    elif file_extension == \'json\':\\n        df = pd.read_json(file_path)\\n    else:\\n        raise ValueError(\'Unsupported file type.\')\\n    return df\\n\\ndf = read_data(\'{file_path}\')\\nprint(df.head())\\n"
}}
```
"""


class FakeUseToolChain(Chain):
    """Fake to use the code-sandbox tool."""

    input_key: str = "input"  #: :meta private:
    output_key: str = "response"  #: :meta private:
    output_parse: JsonOutputParser
    code_sandbox_tool: CodeSandbox

    @classmethod
    def from_memory(
        cls,
        memory: Optional[BaseChatMemory] = None,
        **kwargs: Any,
    ) -> "FakeUseToolChain":
        """Create a DatasetPreviewChain from a memory."""
        code_sandbox_tool = CodeSandbox(
            gateway_url=str(settings.jupyter_enterprise_gateway_url),
            kernel_manager=kernel_manager,
        )
        output_parse = JsonOutputParser()
        return cls(
            memory=memory,
            code_sandbox_tool=code_sandbox_tool,
            output_parse=output_parse,
            **kwargs,
        )

    @property
    def input_keys(self) -> List[str]:
        """Return the singular input key.

        :meta private:
        """
        return [self.input_key]

    @property
    def output_keys(self) -> List[str]:
        """Return the singular output key.

        :meta private:
        """
        return [self.output_key]

    @property
    def _chain_type(self) -> str:
        return "fake-tool-chain"

    def prep_inputs(self, inputs: dict[str, Any] | Any) -> dict[str, str]:
        """Override this method to persist input on chain starts.
        We need to separatly save the input and output on chain starts and ends.
        """
        inputs = super().prep_inputs(inputs)
        if self.memory is not None and isinstance(self.memory, BaseChatMemory):
            message = inputs[self.input_key]
            if isinstance(message, ChatMessage) and isinstance(message.content, File):
                file = message.content
                context = (
                    system.format_map({"file_path": file.path})
                    + os.linesep
                    + code_template.format_map({"file_path": file.path})
                )
                system_message = ChatMessage(
                    content=context, type="text", from_="system"
                )
            else:
                raise ValueError("Illegal input message instance.")
            self.memory.chat_memory.add_message(system_message.to_lc())
            inputs[self.input_key] = context
        return inputs

    def prep_outputs(
        self,
        inputs: dict[str, str],
        outputs: dict[str, any],
        return_only_outputs: bool = False,
    ) -> dict[str, str]:
        """Override this method to disable saving context to memory.
        We need to separatly save the input and output on chain starts and ends.
        """
        self._validate_outputs(outputs)
        if self.memory is not None and isinstance(self.memory, BaseChatMemory):
            tool_result_msg = ChatMessage(
                content=outputs["tool_name"] + os.linesep + outputs[self.output_key],
                type="text",
                from_="tool",
            )
            self.memory.chat_memory.add_message(tool_result_msg.to_lc())
            # Recommended tools
            tool_note_msg = ChatMessage(
                content="Take a deep breath and continue analyzing in code_sandbox.\nNOTE: The user is not allowed to use these tools. Instead, you should use them for the user.",
                type="text",
                from_="tool",
            )
            self.memory.chat_memory.add_message(tool_note_msg.to_lc())
        if return_only_outputs:
            return outputs
        else:
            return {**inputs, **outputs}

    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, Any]:
        # TODO: We cannot send websocket messages in sync method, so ignore this.
        raise NotImplementedError("Synchronous method is not supported yet.")

    async def _acall(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[AsyncCallbackManagerForChainRun] = None,
    ) -> Dict[str, Any]:
        _run_manager = run_manager or AsyncCallbackManagerForChainRun.get_noop_manager()
        input_text = inputs[self.input_key]
        await _run_manager.on_text(input_text, verbose=self.verbose)
        try:
            action = self.output_parse.parse(input_text)
            if not isinstance(action, AgentAction):
                raise ValueError
            result = await self.code_sandbox_tool.arun(action.tool_input)
            return {self.output_key: result, "tool_name": self.code_sandbox_tool.name}
        except Exception as exc:
            raise exc
