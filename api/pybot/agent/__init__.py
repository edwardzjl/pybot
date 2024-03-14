from typing import Sequence

from langchain.agents import AgentOutputParser
from langchain_core.agents import AgentAction, AgentActionMessageLog
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.tools import BaseTool


def construct_scratchpad(
    intermediate_steps: list[tuple[AgentAction, str]]
) -> list[BaseMessage]:
    steps = []
    for action, observation in intermediate_steps:
        if isinstance(action, AgentActionMessageLog):
            steps.extend(action.message_log)
        else:
            steps.append(AIMessage(content=action.log))
        steps.append(SystemMessage(content=observation))
    return steps


def create_agent(
    llm: BaseLanguageModel,
    tools: Sequence[BaseTool],
    prompt: ChatPromptTemplate,
    output_parser: AgentOutputParser,
) -> Runnable:
    tool_descs = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
    prompt = prompt.partial(tools=tool_descs)

    agent = (
        RunnablePassthrough.assign(
            agent_scratchpad=lambda x: construct_scratchpad(x["intermediate_steps"]),
        )
        | prompt
        | llm
        | output_parser
    )
    return agent
