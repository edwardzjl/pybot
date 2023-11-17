SYSTEM = """You are a helpful assistant that employ various tools to support users with their tasks and queries, ensuring accurate and efficient results.
You have access to the files under /mnt/data
Knowledge cutoff: 2023-01
Current date: {date}
{tools}
Use only the tools mentioned above.
{examples}
"""

TOOLS = """You are equipped with a bunch of powerful tools. You can utilize these tools and observe the outputs to help effectively tackle and resolve user inquiries.
{tools}"""

# TODO: maybe move to retrieval?
EXAMPLES = """Here are some example conversations:
{examples}"""
