import ast
import re
from typing import Generator, Union

from langchain.agents import AgentOutputParser
from langchain_core.agents import AgentAction, AgentFinish
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


def parse_python_markdown(source: str) -> str:
    """
    Parse a python code snippet from a Markdown string.

    Args:
        source: The Markdown string.

    Returns:
        The parsed Python code snippet.
    """
    # Try to find Python code within triple backticks
    match = re.search(r"```python\n(.*)```", source, re.DOTALL)

    # If no match found, assume the entire string is a JSON string
    if match is None:
        raise ValueError
    else:
        # If match found, use the content within the backticks
        json_str = match.group(1)

    # Strip whitespace and newlines from the start and end
    json_str = json_str.strip()

    return json_str


class JsonOutputParser(AgentOutputParser):
    """Output parser that extracts all dicts in the output and try to parse them into actions.
    Only the first valid action will be returned.
    The AgentOutputParser is a langchain.load.serializable.Serializable which is a pydantic v1 model in the time of writing.
    """

    tool_name_key: str = "tool_name"
    tool_input_key: str = "tool_input"

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        for _dict, i in find_dicts(text):
            if self.tool_name_key in _dict:
                tool_name = _dict.get(self.tool_name_key)
                tool_input = _dict.get(self.tool_input_key, "")
                return AgentAction(tool_name, tool_input, text[: i + 1])
        # find python markdown code snippet
        try:
            # TODO: this is a fallback workaround
            code = parse_python_markdown(text)
            return AgentAction("code_sandbox", code, text)
        except ValueError:
            return AgentFinish({"output": text}, text)

    @property
    def _type(self) -> str:
        return "json"
