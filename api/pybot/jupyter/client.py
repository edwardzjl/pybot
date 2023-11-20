from urllib.parse import urljoin, urlparse, urlunparse

import requests
from loguru import logger
from pydantic import BaseModel, HttpUrl

from pybot.jupyter.schema import (
    CreateKernelRequest,
    CreateKernelResponse,
    KernelNotFoundException,
)


class GatewayClient(BaseModel):
    host: HttpUrl

    def create_kernel(self, payload: CreateKernelRequest) -> CreateKernelResponse:
        _body = payload.model_dump()
        logger.debug(f"Starting kernel with payload {_body}")
        response = requests.post(urljoin(str(self.host), "/api/kernels"), json=_body)
        if not response.ok:
            raise RuntimeError(
                f"Error starting kernel: {response.status_code}\n{response.content}"
            )
        res = CreateKernelResponse.model_validate_json(response.text)
        logger.info(f"Started kernel with id {res.id}")
        return res

    def get_kernel(self, kernel_id: str) -> CreateKernelResponse:
        response = requests.get(urljoin(str(self.host), f"/api/kernels/{kernel_id}"))
        if response.ok:
            return CreateKernelResponse.model_validate_json(response.text)
        elif response.status_code == 404:
            raise KernelNotFoundException(f"kernel {kernel_id} not found")
        else:
            raise RuntimeError(
                f"Error getting kernel {kernel_id}: {response.status_code}\n{response.content}"
            )

    def delete_kernel(self, kernel_id: str) -> None:
        response = requests.delete(urljoin(str(self.host), f"/api/kernels/{kernel_id}"))
        if not response.ok:
            raise RuntimeError(
                f"Error deleting kernel {kernel_id}: {response.status_code}\n{response.content}"
            )
        logger.info(f"Kernel {kernel_id} deleted")

    def get_ws_endpoint(self, kernel_id: str) -> str:
        base = urlparse(str(self.host))
        ws_scheme = "wss" if base.scheme == "https" else "ws"
        ws_base = urlunparse(base._replace(scheme=ws_scheme))
        return urljoin(ws_base, f"/api/kernels/{kernel_id}/channels")
