import json
import re
from typing import Union

from langchain.agents import AgentOutputParser
from langchain.schema import AgentAction, AgentFinish, OutputParserException
from loguru import logger


class JsonOutputParser(AgentOutputParser):
    """Output parser that referenced langchain.agents.conversational_chat.ConvoOutputParser.
    The AgentOutputParser is a langchain.load.serializable.Serializable which is a pydantic v1 model in the time of writing.
    """

    pattern = re.compile(r"```(?:json)?\n(.*?)```", re.DOTALL)
    tool_name_key: str = "tool_name"
    tool_input_key: str = "tool_input"

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            action_match = self.pattern.search(text)
            if action_match is None:
                # No action match, treat as final answer
                prefix_found = text.find("Final Answer:")  # TODO: final answer key
                if prefix_found != -1:
                    return AgentFinish(
                        {"output": text[prefix_found + 13 :].strip()}, text
                    )
                raise ValueError(
                    f"Could not find action or final answer in LLM output: {text}"
                )

            response: dict = json.loads(action_match.group(1).strip(), strict=False)
            if isinstance(response, list):
                logger.warning(
                    f"Got multiple action responses: {response}, using only the first one."
                )
                response = response[0]
            if self.tool_name_key in response and self.tool_input_key in response:
                tool_name = response.get(self.tool_name_key)
                tool_input = response.get(self.tool_input_key)
                if tool_name == "Final Answer":  # TODO: final answer key
                    return AgentFinish({"output": tool_input}, text)
                return AgentAction(tool_name, tool_input, text)
            else:
                raise ValueError("Not a valid tool response")
        except Exception as e:
            raise OutputParserException(f"Could not parse LLM output: {text}") from e

    @property
    def _type(self) -> str:
        return "json"
