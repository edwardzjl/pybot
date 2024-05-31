from typing import Sequence

from langchain.agents import AgentOutputParser
from langchain_core.agents import AgentAction, AgentActionMessageLog
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from pybot.agent.executor import PybotAgentExecutor
from pybot.agent.output_parser import MarkdownOutputParser
from pybot.agent.prompt import SYSTEM
from pybot.config import settings
from pybot.memory import memory
from pybot.tools import CodeSandbox


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


llm = ChatOpenAI(
    openai_api_base=str(settings.llm.url),
    model=settings.llm.model,
    openai_api_key=settings.llm.creds,
    max_tokens=1024,
    streaming=True,
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM),
        MessagesPlaceholder(variable_name="history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)
tools = [
    CodeSandbox(
        gateway_url=str(settings.jupyter.gateway_url),
    )
]
output_parser = MarkdownOutputParser(language_actions={"python": "python"})
agent = create_agent(llm, tools, prompt, output_parser)
agent_executor = PybotAgentExecutor(
    agent=agent, tools=tools, memory=memory, handle_parsing_errors=True
)
