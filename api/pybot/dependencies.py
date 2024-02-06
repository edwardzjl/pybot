from typing import Annotated, Optional

from fastapi import Depends, Header
from langchain.agents import AgentExecutor
from langchain.chains.base import Chain
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_community.llms.huggingface_text_gen_inference import (
    HuggingFaceTextGenInference,
)
from langchain_core.language_models import BaseLLM
from langchain_core.memory import BaseMemory

from pybot.agent.base import create_agent
from pybot.callbacks import TracingLLMCallbackHandler
from pybot.chains import SummarizationChain
from pybot.config import settings
from pybot.history import PybotMessageHistory
from pybot.memory import PybotMemory
from pybot.prompts.chatml import AI_SUFFIX
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
    return HuggingFaceTextGenInference(
        inference_server_url=str(settings.inference_server_url),
        max_new_tokens=1024,
        temperature=None,
        # top_p=0.9,
        stop_sequences=[
            AI_SUFFIX
        ],  # not all mistral models have a decent tokenizer config.
        streaming=True,
        callbacks=[TracingLLMCallbackHandler()],
    )


def PybotAgent(
    llm: Annotated[BaseLLM, Depends(Llm)],
    memory: Annotated[BaseMemory, Depends(ChatMemory)],
) -> AgentExecutor:
    tools = [
        CodeSandbox(
            gateway_url=str(settings.jupyter.gateway_url),
        )
    ]
    return create_agent(
        llm=llm,
        tools=tools,
        agent_executor_kwargs={
            "memory": memory,
            "return_intermediate_steps": True,
        },
    )


def SmryChain(
    llm: Annotated[BaseLLM, Depends(Llm)],
    memory: Annotated[BaseMemory, Depends(ChatMemory)],
) -> Chain:
    return SummarizationChain(
        llm=llm,
        memory=memory,
    )
