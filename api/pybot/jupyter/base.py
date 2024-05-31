from abc import ABC, abstractmethod
from typing import Optional

from loguru import logger
from pydantic import BaseModel


class CodeExecutionException(RuntimeError): ...


class KernelNotFoundException(RuntimeError): ...


class Kernel(BaseModel, ABC):
    id: str
    """ID of the kernel"""

    @abstractmethod
    def execute_code(self, code: str, **kwargs) -> str:
        """Execute code in the kernel and return the result as a string.

        Args:
            code (str): code to execute

        Returns:
            str: result of the code execution

        Raises:
            CodeExecutionException: if the code execution fails
        """

    def aexecute_code(self, code: str, **kwargs) -> str:
        """Asynchoronously execute code in the kernel and return the result as a string.
        Default implementation is to call the synchronous `execute_code` method.

        Args:
            code (str): code to execute

        Returns:
            str: result of the code execution

        Raises:
            CodeExecutionException: if the code execution fails
        """
        return self.execute_code(code=code, **kwargs)


class KernelManager(ABC):
    """Abstract Base class for managing kernels"""

    def get_or_create_kernel(
        self,
        kernel_id: Optional[str] = None,
        **kwargs,
    ) -> Kernel:
        """Retrieve an existing kernel or create a new one."""
        try:
            return self._get_kernel(kernel_id=kernel_id, **kwargs)
        except KernelNotFoundException:
            try:
                kernel = self._create_kernel(**kwargs)
            except Exception as e:
                logger.error(f"Error during kernel startup: {e}")
                raise e

            return kernel

    @abstractmethod
    def _get_kernel(
        self,
        kernel_id: Optional[str] = None,
        **kwargs,
    ) -> Kernel:
        """Retrieve an existing kernel by its ID."""
        ...

    @abstractmethod
    def _create_kernel(self, **kwargs) -> Kernel:
        """Create a new kernel."""
        ...

    async def aget_or_create_kernel(
        self,
        kernel_id: Optional[str] = None,
        **kwargs,
    ) -> Kernel:
        """Retrieve an existing kernel or create a new one."""
        try:
            kernel = await self._aget_kernel(kernel_id=kernel_id, **kwargs)
            return kernel
        except KernelNotFoundException:
            try:
                kernel = await self._acreate_kernel(**kwargs)
            except Exception as e:
                logger.error(f"Error during kernel startup: {e}")
                raise e

            return kernel

    async def _aget_kernel(
        self,
        kernel_id: Optional[str] = None,
        **kwargs,
    ) -> Kernel:
        """Retrieve an existing kernel by its ID."""
        self._get_kernel(kernel_id=kernel_id, **kwargs)

    async def _acreate_kernel(self, **kwargs) -> Kernel:
        """Create a new kernel."""
        return self._create_kernel(**kwargs)
