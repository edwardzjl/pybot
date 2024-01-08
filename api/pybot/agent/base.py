from typing import Any, Optional, Sequence

from langchain.agents import Agent, AgentExecutor, AgentOutputParser
from langchain.memory.chat_memory import BaseChatMemory
from langchain_core.agents import AgentAction
from langchain_core.language_models import BaseLanguageModel
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
from pybot.memory import PybotMemory
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


class CustomAgentExecutor(AgentExecutor):
    """agent executor that persists intermediate steps.
    It also separate the persistance of input and output, so that when error occurs, the input is persisted.
    """

    def prep_inputs(self, inputs: dict[str, Any] | Any) -> dict[str, str]:
        """Prepare and persist inputs."""
        inputs = super().prep_inputs(inputs)
        if self.memory is not None and isinstance(self.memory, PybotMemory):
            self.memory.history.add_user_message(inputs[self.memory.input_key])
        if self.memory is not None and isinstance(self.memory, BaseChatMemory):
            self.memory.chat_memory.add_user_message(inputs[self.memory.input_key])
        return inputs

    def prep_outputs(
        self,
        inputs: dict[str, str],
        outputs: dict[str, str],
        return_only_outputs: bool = False,
    ) -> dict[str, str]:
        """Prepare and persist outputs."""
        self._validate_outputs(outputs)
        additional_kwargs = (
            {"intermediate_steps": outputs["intermediate_steps"]}
            if "intermediate_steps" in outputs
            else {}
        )
        if self.memory is not None and isinstance(self.memory, PybotMemory):
            msg = AIMessage(
                content=outputs[self.memory.output_key],
                additional_kwargs=additional_kwargs,
            )
            self.memory.history.add_message(msg)
        if self.memory is not None and isinstance(self.memory, BaseChatMemory):
            msg = AIMessage(
                content=outputs[self.memory.output_key],
                additional_kwargs=additional_kwargs,
            )
            self.memory.chat_memory.add_message(msg)
        if return_only_outputs:
            return outputs
        else:
            return {**inputs, **outputs}


def create_agent(
    llm: BaseLanguageModel,
    tools: list[BaseTool],
    max_iterations: Optional[int] = 15,
    max_execution_time: Optional[float] = None,
    early_stopping_method: str = "force",
    verbose: bool = False,
    agent_executor_kwargs: Optional[dict[str, Any]] = None,
    **kwargs: dict[str, Any],
) -> AgentExecutor:
    """Construct an SQL agent from an LLM and tools."""
    agent = PybotAgent.from_llm_and_tools(
        llm=llm,
        tools=tools,
        **kwargs,
    )
    return CustomAgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=verbose,
        max_iterations=max_iterations,
        max_execution_time=max_execution_time,
        early_stopping_method=early_stopping_method,
        **(agent_executor_kwargs or {}),
    )
