from operator import itemgetter
from typing import Optional

from fastapi import Header
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

from pybot.agent import create_agent
from pybot.agent.executor import PybotAgentExecutor
from pybot.agent.output_parser import MarkdownOutputParser
from pybot.agent.prompt import SYSTEM
from pybot.chains.summarization import tmpl
from pybot.config import settings
from pybot.history import PybotMessageHistory
from pybot.memory import PybotMemory
from pybot.tools import CodeSandbox


def UserIdHeader(alias: Optional[str] = None, **kwargs):
    if alias is None:
        alias = settings.user_id_header
    return Header(alias=alias, **kwargs)


def UsernameHeader(alias: Optional[str] = None, **kwargs):
    if alias is None:
        alias = "X-Forwarded-Preferred-Username"
    return Header(alias=alias, **kwargs)


def EmailHeader(alias: Optional[str] = None, **kwargs):
    if alias is None:
        alias = "X-Forwarded-Email"
    return Header(alias=alias, **kwargs)


llm = ChatOpenAI(
    openai_api_base=str(settings.llm.url),
    model=settings.llm.model,
    openai_api_key=settings.llm.creds,
    max_tokens=1024,
    streaming=True,
)

history = PybotMessageHistory(
    url=str(settings.redis_om_url),
    key_prefix="chatbot:messages:",
    session_id="sid",  # a fake session id as it is required
)

memory = PybotMemory(
    memory_key="history",
    input_key="input",
    history=history,
    return_messages=True,
)

smry_chain = (
    {"history": RunnableLambda(memory.load_memory_variables) | itemgetter("history")}
    | tmpl
    | llm
    | StrOutputParser()
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
