from langchain.agents import AgentExecutor


class PybotAgentExecutor(AgentExecutor):
    """agent executor that disables persists messages to memory.
    I handle the memory saving myself."""

    def prep_outputs(
        self,
        inputs: dict[str, str],
        outputs: dict[str, str],
        return_only_outputs: bool = False,
    ) -> dict[str, str]:
        """Override this method to disable saving context to memory."""
        self._validate_outputs(outputs)
        if return_only_outputs:
            return outputs
        else:
            return {**inputs, **outputs}
