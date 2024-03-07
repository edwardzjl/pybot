from typing import Sequence

from langchain.agents import AgentOutputParser
from langchain_core.agents import AgentAction, AgentActionMessageLog
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.tools import BaseTool

from pybot.agent.prompt import EXAMPLES
from pybot.tools.base import ExtendedTool


def construct_scratchpad(
    intermediate_steps: list[tuple[AgentAction, str]]
) -> list[BaseMessage]:
    steps = []
    for action, observation in intermediate_steps:
        if isinstance(action, AgentActionMessageLog):
            steps.append(action.message_log[0])
        else:
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


def create_agent(
    llm: BaseLanguageModel,
    tools: Sequence[BaseTool],
    prompt: ChatPromptTemplate,
    output_parser: AgentOutputParser,
) -> Runnable:

    missing_vars = {"tools", "agent_scratchpad"}.difference(prompt.input_variables)
    if missing_vars:
        raise ValueError(f"Prompt missing required variables: {missing_vars}")

    tool_descs = "\n".join([f"{tool.description}" for tool in tools])
    # TODO: maybe extract examples to some retrieval
    ext_tools: list[ExtendedTool] = list(
        filter(lambda tool: isinstance(tool, ExtendedTool), tools)
    )
    examples = "\n".join([f"{tool.examples}" for tool in ext_tools])
    examples_strings = EXAMPLES.format(examples=examples)

    prompt = prompt.partial(
        tools=tool_descs,
        examples=examples_strings,
    )

    agent = (
        RunnablePassthrough.assign(
            agent_scratchpad=lambda x: construct_scratchpad(x["intermediate_steps"]),
        )
        | prompt
        | llm
        | output_parser
    )
    return agent
