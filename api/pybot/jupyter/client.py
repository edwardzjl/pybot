from urllib.parse import urljoin

import requests
from loguru import logger
from pydantic import BaseModel, HttpUrl

from pybot.jupyter.schema import CreateKernelRequest, Kernel, KernelNotFoundException


class GatewayClient(BaseModel):
    host: HttpUrl

    def create_kernel(self, payload: CreateKernelRequest) -> Kernel:
        _body = payload.model_dump()
        logger.debug(f"Starting kernel with payload {_body}")
        response = requests.post(urljoin(str(self.host), "/api/kernels"), json=_body)
        if not response.ok:
            raise RuntimeError(
                f"Error starting kernel: {response.status_code}\n{response.content}"
            )
        res = Kernel.model_validate_json(response.text)
        logger.info(f"Started kernel with id {res.id}")
        return res

    def get_kernel(self, kernel_id: str) -> Kernel:
        response = requests.get(urljoin(str(self.host), f"/api/kernels/{kernel_id}"))
        if response.ok:
            return Kernel.model_validate_json(response.text)
        elif response.status_code == 404:
            raise KernelNotFoundException(f"kernel {kernel_id} not found")
        else:
            raise RuntimeError(
                f"Error getting kernel {kernel_id}: {response.status_code}\n{response.content}"
            )

    def delete_kernel(self, kernel_id: str) -> None:
        response = requests.delete(urljoin(str(self.host), f"/api/kernels/{kernel_id}"))
        if not response.ok:
            if response.status_code == 404:
                raise KernelNotFoundException(f"kernel {kernel_id} not found")
            else:
                raise RuntimeError(
                    f"Error deleting kernel {kernel_id}: {response.status_code}\n{response.content}"
                )
        logger.info(f"Kernel {kernel_id} deleted")
