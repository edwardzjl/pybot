from langchain.llms import BaseLLM
from langchain.llms.huggingface_text_gen_inference import HuggingFaceTextGenInference
from langchain.memory import RedisChatMessageHistory

from pybot.config import settings
from pybot.history import CustomRedisChatMessageHistory


def get_message_history() -> RedisChatMessageHistory:
    return CustomRedisChatMessageHistory(
        url=str(settings.redis_om_url),
        session_id="sid",  # a fake session id as it is required
    )


def get_llm() -> BaseLLM:
    return HuggingFaceTextGenInference(
        inference_server_url=str(settings.inference_server_url),
        max_new_tokens=1024,
        temperature=0.8,
        top_p=0.9,
        repetition_penalty=1.01,
        stop_sequences=["</s>"],
        streaming=True,
    )
