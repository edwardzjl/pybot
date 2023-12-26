from langchain_core.tools import BaseTool


class ExtendedTool(BaseTool):
    examples: str = ""
