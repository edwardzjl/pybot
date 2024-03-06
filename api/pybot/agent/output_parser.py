import ast
import re
from typing import Generator

from langchain.agents import AgentOutputParser
from langchain_core.agents import AgentAction, AgentActionMessageLog, AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage
from loguru import logger


def find_dicts(s: str) -> Generator[tuple[dict, int], None, None]:
    """find dicts in a string
    Modified from <https://stackoverflow.com/a/51862122/6564721>

    Args:
        s (str): source string

    Yields:
        Generator[tuple[dict, int], None, None]: generates a tuple of dict and the index of the last char of the dict
    """
    stack = []  # a stack to keep track of the brackets
    buffer = ""  # a buffer to store current tracking string
    for i, ch in enumerate(s):
        if ch == "{":
            buffer += ch
            stack.append(ch)
        elif ch == "}":
            stack.pop(-1)
            buffer += ch
            if not stack:
                try:
                    yield ast.literal_eval(buffer), i
                except ValueError:
                    # LLM could generate non-dict {} pairs, which is also valid
                    # So I only set the log level to debug, and continue searching.
                    logger.debug(f"Failed to parse {buffer} into a dict")
                buffer = ""
        elif stack:
            buffer += ch


class ComposedOutputParser(AgentOutputParser):
    parsers: list[AgentOutputParser] = []
    just_finish: bool = True
    """Whether to just return AgentFinish if no parser can parse the output. Default to True."""

    def parse(self, text: str) -> AgentAction | AgentFinish:
        for parser in self.parsers:
            try:
                return parser.parse(text)
            except OutputParserException:
                continue
        if self.just_finish:
            return AgentFinish({"output": text}, text)
        raise OutputParserException(f"Could not parse output: {text}")

    @property
    def _type(self) -> str:
        return "composed"


class MarkdownOutputParser(AgentOutputParser):
    """Output parser that extracts markdown code blocks and try to parse them into actions."""

    pattern = re.compile(r"([\S\s]*)`{3}([\w]*)\n([\S\s]+?)\n`{3}", re.DOTALL)
    language_actions: dict[str, str] = {}
    """A mapping from language to action key."""

    def parse(self, text: str) -> AgentAction | AgentFinish:
        if (match := re.search(self.pattern, text)) is not None:
            if (action := self.language_actions.get(match.group(2))) is not None:
                return AgentActionMessageLog(
                    tool=action,
                    tool_input=match.group(3),
                    log=match.group(1),  # log is the 'thought' part
                    message_log=[
                        AIMessage(content=text)
                    ],  # message_log is the content we can add to history
                )
            logger.warning(f"Unknown language {match.group(2)}")
        raise OutputParserException(f"Could not parse output: {text}")

    @property
    def _type(self) -> str:
        return "markdown"


class DictOutputParser(AgentOutputParser):
    """Output parser that extracts all dicts in the output and try to parse them into actions.
    Only the first valid action will be returned.
    The AgentOutputParser is a langchain.load.serializable.Serializable which is a pydantic v1 model in the time of writing.
    """

    tool_name_key: str = "tool_name"
    tool_input_key: str = "tool_input"

    def parse(self, text: str) -> AgentAction | AgentFinish:
        for _dict, i in find_dicts(text):
            if self.tool_name_key in _dict:
                tool_name = _dict.get(self.tool_name_key)
                tool_input = _dict.get(self.tool_input_key, "")
                return AgentActionMessageLog(
                    tool=tool_name,
                    tool_input=tool_input,
                    log=text[: i + 1],  # log is the 'thought' part
                    message_log=[
                        AIMessage(content=text)
                    ],  # message_log is the content we can add to history
                )
        raise OutputParserException(f"Could not parse output: {text}")

    @property
    def _type(self) -> str:
        return "json"
