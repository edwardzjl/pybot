import queue
from typing import Any, Optional
from uuid import uuid4

from loguru import logger

from pybot.jupyter.base import (
    CodeExecutionException,
    Kernel,
    KernelManager,
    KernelNotFoundException,
)
from pybot.jupyter.utils import clean_ansi_codes


def kernel_result_processor(
    shell_msg: dict[str, Any], iopub_msg: dict[str, Any]
) -> tuple[str, str]:
    """Process the result from kernel execution.

    Args:
        shell_msg (dict[str, Any]): kernel execution status message
        iopub_msg (dict[str, Any]): kernel execution result message

    Returns:
        tuple[str, str]: Result type and the result.
            Result type could be one of "text", "image", "error", "aborted" or "unknown"
    """
    # One of: 'ok' OR 'error' OR 'aborted'
    status = shell_msg["content"]["status"]
    if status == "error":
        return "error", clean_ansi_codes("\n".join(iopub_msg["traceback"]))
    elif status == "aborted":
        return "aborted", ""

    if "text" in iopub_msg:
        res_type = "text"
        res = iopub_msg["text"]
    elif "data" in iopub_msg:
        for key in iopub_msg["data"]:
            if "text/plain" in key:
                res_type = "text"
                res = iopub_msg["data"][key]
            elif "image/png" in key:
                res_type = "image"
                res = iopub_msg["data"][key]
                break
    else:
        logger.debug(f"Unhandled iopub message: {iopub_msg}")
        res_type = "unknown"
        # TODO: json str?
        res = str(iopub_msg)

    return res_type, res


class IPyKernel(Kernel):
    client: Any

    def execute_code(self, code: str, **kwargs) -> str:
        if not self.client.channels_running:
            self.client.wait_for_ready()

        self.client.execute(code)

        shell_msg, iopub_msg = self.__get_kernel_output()
        result_type, result = kernel_result_processor(
            shell_msg=shell_msg, iopub_msg=iopub_msg
        )
        if result_type in ["traceback", "error"]:
            raise CodeExecutionException(result)
        # TODO: retry on aborted?
        logger.debug(
            f"kernel execution code {code}, result_type: {result_type}, result: {result} "
        )
        return result

    async def aexecute_code(self, code: str, **kwargs) -> str:
        if not self.client.channels_running:
            await self.client._async_wait_for_ready()

        self.client.execute(code)

        shell_msg, iopub_msg = await self.__aget_kernel_output()
        result_type, result = kernel_result_processor(
            shell_msg=shell_msg, iopub_msg=iopub_msg
        )
        if result_type in ["traceback", "error"]:
            raise CodeExecutionException(result)
        # TODO: retry on aborted?
        logger.debug(
            f"kernel execution code {code}, result_type: {result_type}, result: {result} "
        )
        return result

    def __get_kernel_output(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Retrieves output from a kernel.

        Returns:
            tuple[dict[str, Any], dict[str, Any]]: (shell_message, iopub_message)
              where shell_message represents the execution status and iopub_message represents the execution result.
              See [shell_message](https://jupyter-client.readthedocs.io/en/stable/messaging.html#messages-on-the-shell-router-dealer-channel)
              and [iopub_message](https://jupyter-client.readthedocs.io/en/stable/messaging.html#messages-on-the-iopub-pub-sub-channel)
        """
        shell_msg = None
        while True:
            try:
                shell_msg = self.client.get_shell_msg(timeout=30)
                if shell_msg["msg_type"] == "execute_reply":
                    break
            except queue.Empty:
                logger.warning(f"Get shell msg is empty.")
                break
        iopub_msg = None
        while True:
            # Poll the message
            try:
                io_msg_content = self.client.get_iopub_msg(timeout=30)["content"]
                if (
                    "execution_state" in io_msg_content
                    and io_msg_content["execution_state"] == "idle"
                ):
                    break
                iopub_msg = io_msg_content
            except queue.Empty:
                logger.warning(f"Get iopub msg is empty.")
                break

        logger.debug(
            f"Got kernel output, shell_msg: {shell_msg} iopub_msg: {iopub_msg}"
        )
        return shell_msg, iopub_msg

    async def __aget_kernel_output(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Retrieves output from a kernel asynchronously.

        Returns:
            tuple[dict[str, Any], dict[str, Any]]: (shell_message, iopub_message)
              where shell_message represents the execution status and iopub_message represents the execution result.
              See [shell_message](https://jupyter-client.readthedocs.io/en/stable/messaging.html#messages-on-the-shell-router-dealer-channel)
              and [iopub_message](https://jupyter-client.readthedocs.io/en/stable/messaging.html#messages-on-the-iopub-pub-sub-channel)
        """
        shell_msg = None
        while True:
            try:
                shell_msg = await self.client._async_get_shell_msg(timeout=30)
                if shell_msg["msg_type"] == "execute_reply":
                    break
            except queue.Empty:
                logger.warning(f"Get shell msg is empty.")
                break

        iopub_msg = None
        while True:
            # Poll the message
            try:
                io_msg = await self.client._async_get_iopub_msg(timeout=30)
                io_msg_content = io_msg["content"]
                if (
                    "execution_state" in io_msg_content
                    and io_msg_content["execution_state"] == "idle"
                ):
                    break
                iopub_msg = io_msg_content
            except queue.Empty:
                logger.warning(f"Get iopub msg is empty.")
                break

        logger.debug(
            f"Got kernel output, shell_msg: {shell_msg} iopub_msg: {iopub_msg}"
        )
        return shell_msg, iopub_msg


class LocalKernelManager(KernelManager):
    def __init__(self):
        try:
            from jupyter_client import MultiKernelManager
        except ImportError:
            raise ImportError(
                "LocalKernelManager is not recommended for production use."
                "For local development, please use `pipenv install --dev` to install related dependencies."
            )
        # We do not additionally import AsyncMultiKernelManager.
        self.manager = MultiKernelManager()

    def __del__(self):
        """clean up all the kernels."""
        logger.info("Shutting down all kernels")
        self.manager.shutdown_all(now=True)
        self.manager.__del__()

    def _create_kernel(self, **kwargs) -> Kernel:
        kernel_id = uuid4().hex
        logger.debug(f"Starting new kernel with ID {kernel_id}")
        self.manager.start_kernel(kernel_id=kernel_id, **kwargs)
        km = self.manager.get_kernel(kernel_id=kernel_id)
        return IPyKernel(id=kernel_id, client=km.client())

    def _get_kernel(
        self,
        kernel_id: Optional[str] = None,
        **kwargs,
    ) -> IPyKernel:
        try:
            km = self.manager.get_kernel(kernel_id=kernel_id)
        except KeyError:
            raise KernelNotFoundException(f"kernel {kernel_id} not found")
        return IPyKernel(id=kernel_id, client=km.client())

    async def _acreate_kernel(
        self,
        **kwargs,
    ) -> Kernel:
        kernel_id = uuid4().hex
        logger.debug(f"Starting new kernel with ID {kernel_id}")
        await self.manager._async_start_kernel(kernel_id=kernel_id, **kwargs)
        km = self.manager.get_kernel(kernel_id=kernel_id)
        return IPyKernel(id=kernel_id, client=km.client())
