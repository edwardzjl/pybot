from typing import Annotated, Optional

from fastapi import Depends, Header
from langchain.agents import AgentExecutor
from langchain.chains.base import Chain
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.language_models import BaseLLM
from langchain_core.memory import BaseMemory
from langchain_openai import ChatOpenAI

from pybot.agent import PybotAgent
from pybot.agent.executor import PybotAgentExecutor
from pybot.agent.output_parser import (
    ComposedOutputParser,
    DictOutputParser,
    MarkdownOutputParser,
)
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
        model="cognitivecomputations/dolphin-2.6-mistral-7b-dpo-laser",  # this does not matter
        openai_api_key="EMPTY",
        openai_api_base=str(settings.inference_server_url),
        max_tokens=1024,
        streaming=True,
    )


def PbAgent(
    llm: Annotated[BaseLLM, Depends(Llm)],
    memory: Annotated[BaseMemory, Depends(ChatMemory)],
) -> AgentExecutor:
    tools = [
        CodeSandbox(
            gateway_url=str(settings.jupyter.gateway_url),
        )
    ]
    markdown_parser = MarkdownOutputParser(language_actions={"python": "python"})
    dict_parser = DictOutputParser()
    output_parser = ComposedOutputParser(
        parsers=[markdown_parser, dict_parser],
        just_finish=True,
    )
    agent = PybotAgent.from_llm_and_tools(
        llm=llm,
        tools=tools,
        output_parser=output_parser,
    )
    return PybotAgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=False,
        max_iterations=15,
        max_execution_time=None,
        early_stopping_method="force",
        return_intermediate_steps=True,
    )


def SmryChain(
    llm: Annotated[BaseLLM, Depends(Llm)],
    memory: Annotated[BaseMemory, Depends(ChatMemory)],
) -> Chain:
    return SummarizationChain(
        llm=llm,
        memory=memory,
    )
