from urllib.parse import urljoin

import requests
from loguru import logger
from pydantic import BaseModel, HttpUrl

from pybot.jupyter.schema import CreateKernelRequest, CreateKernelResponse


class Client(BaseModel):
    host: HttpUrl

    def create_kernel(self, payload: CreateKernelRequest) -> None:
        response = requests.post(
            urljoin(str(self.host), "/api/kernels"), json=payload.model_dump()
        )
        if response.ok:
            res = CreateKernelResponse.model_validate_json(response.text)
            logger.info(f"Started kernel with id {res.id}")
        else:
            raise RuntimeError(
                f"Error starting kernel: {response.status_code}\n{response.content}"
            )

    def get_kernel(self, kernel_id: str) -> CreateKernelRequest:
        response = requests.get(urljoin(str(self.host), f"/api/kernels/{kernel_id}"))
        if response.ok:
            return CreateKernelResponse.model_validate_json(response.text)
        elif response.status_code == 404:
            # TODO: Handle 404
            raise RuntimeError(f"kernel {kernel_id} not found")
        else:
            raise RuntimeError(
                f"Error getting kernel {kernel_id}: {response.status_code}\n{response.content}"
            )

    def delete_kernel(self, kernel_id: str) -> None:
        response = requests.delete(urljoin(str(self.host), f"/api/kernels/{kernel_id}"))
        if response.ok:
            logger.info(f"Kernel {kernel_id} deleted")
        else:
            raise RuntimeError(
                f"Error deleting kernel {kernel_id}: {response.status_code}\n{response.content}"
            )
