from langchain.tools import BaseTool


class ExtendedTool(BaseTool):
    examples: str = ""
