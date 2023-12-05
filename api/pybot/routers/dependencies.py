from typing import Annotated, Optional

from fastapi import Depends, Header
from langchain.llms import BaseLLM
from langchain.llms.huggingface_text_gen_inference import HuggingFaceTextGenInference
from langchain.memory import ConversationBufferWindowMemory, RedisChatMessageHistory
from langchain.schema import BaseMemory

from pybot.callbacks import TracingLLMCallbackHandler
from pybot.config import settings
from pybot.history import ContextAwareMessageHistory
from pybot.prompts import AI_PREFIX, AI_SUFFIX, HUMAN_PREFIX


def UserIdHeader(alias: Optional[str] = None, **kwargs):
    if alias is None:
        alias = settings.user_id_header
    return Header(alias=alias, **kwargs)


def get_message_history() -> RedisChatMessageHistory:
    return ContextAwareMessageHistory(
        url=str(settings.redis_om_url),
        key_prefix="pybot:messages:",
        session_id="sid",  # a fake session id as it is required
    )


def get_memory(
    history: Annotated[RedisChatMessageHistory, Depends(get_message_history)]
) -> BaseMemory:
    return ConversationBufferWindowMemory(
        human_prefix=HUMAN_PREFIX,
        ai_prefix=AI_PREFIX,
        memory_key="history",
        input_key="input",
        output_key="output",
        chat_memory=history,
        return_messages=True,
    )


def get_llm() -> BaseLLM:
    return HuggingFaceTextGenInference(
        inference_server_url=str(settings.inference_server_url),
        max_new_tokens=1024,
        temperature=0.1,
        top_p=0.9,
        stop_sequences=[
            AI_SUFFIX
        ],  # not all mistral models have a decent tokenizer config.
        streaming=True,
        callbacks=[TracingLLMCallbackHandler()],
    )
