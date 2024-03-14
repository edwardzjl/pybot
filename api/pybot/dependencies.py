from typing import Annotated, Optional

from fastapi import Depends, Header
from langchain.agents import AgentExecutor
from langchain.chains.base import Chain
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.language_models import BaseLLM
from langchain_core.memory import BaseMemory
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI

from pybot.agent import create_agent
from pybot.agent.executor import PybotAgentExecutor
from pybot.agent.output_parser import MarkdownOutputParser
from pybot.agent.prompt import SYSTEM
from pybot.chains import SummarizationChain
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


def MessageHistory() -> RedisChatMessageHistory:
    return PybotMessageHistory(
        url=str(settings.redis_om_url),
        key_prefix="pybot:messages:",
        session_id="sid",  # a fake session id as it is required
    )


def ChatMemory(
    history: Annotated[RedisChatMessageHistory, Depends(MessageHistory)]
) -> BaseMemory:
    return PybotMemory(
        memory_key="history",
        input_key="input",
        output_key="output",
        history=history,
        return_messages=True,
    )


def Llm() -> BaseLLM:
    return ChatOpenAI(
        openai_api_base=str(settings.llm.url),
        openai_api_key=settings.llm.creds,
        model=settings.llm.model,
        max_tokens=1024,
        streaming=True,
    )


def PbAgent(
    llm: Annotated[BaseLLM, Depends(Llm)],
    memory: Annotated[BaseMemory, Depends(ChatMemory)],
) -> AgentExecutor:
    messages = [
        SystemMessagePromptTemplate.from_template(SYSTEM),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
    prompt = ChatPromptTemplate(messages=messages)
    tools = [
        CodeSandbox(
            gateway_url=str(settings.jupyter.gateway_url),
        )
    ]
    output_parser = MarkdownOutputParser(language_actions={"python": "python"})

    agent = create_agent(llm, tools, prompt, output_parser)

    return PybotAgentExecutor(
        agent=agent, tools=tools, memory=memory, handle_parsing_errors=True
    )


def SmryChain(
    llm: Annotated[BaseLLM, Depends(Llm)],
    memory: Annotated[BaseMemory, Depends(ChatMemory)],
) -> Chain:
    return SummarizationChain(
        llm=llm,
        memory=memory,
    )
