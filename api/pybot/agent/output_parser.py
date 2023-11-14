import json
import re
from typing import Union

from langchain.agents import AgentOutputParser
from langchain.schema import AgentAction, AgentFinish
from loguru import logger


class JsonOutputParser(AgentOutputParser):
    """Output parser that referenced langchain.agents.conversational_chat.ConvoOutputParser.
    The AgentOutputParser is a langchain.load.serializable.Serializable which is a pydantic v1 model in the time of writing.
    """

    pattern = re.compile(
        r"(?:```)?(?:json)?\n(\{\s*\"tool_name\":.*?})\n(?:```)?", re.DOTALL
    )
    tool_name_key: str = "tool_name"
    tool_input_key: str = "tool_input"

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        try:
            md_snippet_match = self.pattern.search(text)
            if md_snippet_match is None:
                # no markdown snippet, try to parse as raw json string
                action_str: str = text.strip()
                # sometimes LLM will generate action with thoughts or halucinations, we will extract the action part
                action_str = action_str[
                    action_str.index("{") : action_str.rindex("}") + 1
                ]
                action: dict = json.loads(action_str, strict=False)
                return AgentAction(
                    action.get(self.tool_name_key),
                    action.get(self.tool_input_key),
                    text,
                )
            action: dict = json.loads(md_snippet_match.group(1).strip(), strict=False)
            if isinstance(action, list):
                logger.warning(
                    f"Got multiple action responses: {action}, using only the first one."
                )
                action = action[0]
            if self.tool_name_key in action and self.tool_input_key in action:
                tool_name = action.get(self.tool_name_key)
                tool_input = action.get(self.tool_input_key)
                if tool_name == "Final Answer":  # TODO: final answer key
                    return AgentFinish({"output": tool_input}, text)
                return AgentAction(tool_name, tool_input, text)
            else:
                raise ValueError("Not a valid tool response")
        except Exception as e:
            logger.error(f"Could not parse LLM output: {text}, error: {str(e)}")
            return AgentFinish({"output": text}, text)

    @property
    def _type(self) -> str:
        return "json"
