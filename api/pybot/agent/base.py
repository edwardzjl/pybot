from typing import Any, Optional, Sequence

from langchain.agents import Agent, AgentExecutor, AgentOutputParser
from langchain_core.agents import AgentAction
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.prompts import (
    BasePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.tools import BaseTool
from pydantic.v1 import Field

from pybot.agent.output_parser import JsonOutputParser
from pybot.agent.prompt import EXAMPLES, SYSTEM, TOOLS
from pybot.prompts.chatml import ChatMLPromptTemplate
from pybot.tools.base import ExtendedTool


class PybotAgent(Agent):
    """Agent that referenced langchain.agents.conversational_chat.base.ConversationalChatAgent"""

    output_parser: Optional[AgentOutputParser] = Field(default_factory=JsonOutputParser)

    @classmethod
    def create_prompt(cls, tools: Sequence[BaseTool]) -> BasePromptTemplate:
        tool_descs = "\n".join([f"{tool.description}" for tool in tools])
        tool_strings = TOOLS.format(tools=tool_descs)

        ext_tools: list[ExtendedTool] = list(
            filter(lambda tool: isinstance(tool, ExtendedTool), tools)
        )
        examples = "\n".join([f"{tool.examples}" for tool in ext_tools])
        examples_strings = EXAMPLES.format(examples=examples)

        system_prompt = PromptTemplate(
            template=SYSTEM,
            input_variables=["date"],
            partial_variables={"tools": tool_strings, "examples": examples_strings},
        )
        messages = [
            SystemMessagePromptTemplate(prompt=system_prompt),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
        return ChatMLPromptTemplate(
            input_variables=["date", "input", "agent_scratchpad"], messages=messages
        )

    def _construct_scratchpad(
        self, intermediate_steps: list[tuple[AgentAction, str]]
    ) -> list[BaseMessage]:
        steps = []
        for action, observation in intermediate_steps:
            steps.append(AIMessage(content=action.log))
            steps.append(
                SystemMessage(
                    content=observation,
                    additional_kwargs={
                        "prefix": f"<|im_start|>{action.tool}\n",
                        "suffix": "<|im_end|>",
                    },
                )
            )
        return steps

    @classmethod
    def _get_default_output_parser(cls, **kwargs: Any) -> AgentOutputParser:
        """Get default output parser for this class."""
        return JsonOutputParser()

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "<|im_start|>system observation\n"

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the LLM call with."""
        return "<|im_start|>assistant\n"


class PybotAgentExecutor(AgentExecutor):
    """agent executor that disables persists messages to memory.
    I handle the memory saving myself."""

    def prep_outputs(
        self,
        inputs: dict[str, str],
        outputs: dict[str, str],
        return_only_outputs: bool = False,
    ) -> dict[str, str]:
        """Override this method to disable saving context to memory."""
        self._validate_outputs(outputs)
        if return_only_outputs:
            return outputs
        else:
            return {**inputs, **outputs}
