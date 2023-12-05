from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

from loguru import logger
from websockets.client import connect as aconnect
from websockets.sync.client import connect

from pybot.config import settings
from pybot.context import session_id
from pybot.jupyter import GatewayClient
from pybot.jupyter.schema import CreateKernelRequest, Kernel, KernelNotFoundException
from pybot.session import RedisSessionStore


class ContextAwareKernelManager:
    def __init__(self, gateway_host):
        self.gateway_host = gateway_host
        self.gateway_client = GatewayClient(host=gateway_host)
        self.session_store = RedisSessionStore()

    def start_kernel(self) -> Kernel:
        sid = session_id.get()
        session = self.session_store.get(sid)
        try:
            return self.gateway_client.get_kernel(session.kernel_id)
        except KernelNotFoundException:
            logger.debug("kernel not found, creating a new one.")
            env = self._get_kernel_env(session.user_id, session.conv_id)
            request = CreateKernelRequest(env=env)
            res = self.gateway_client.create_kernel(request)
            session.kernel_id = str(res.id)
            self.session_store.save(session)
            return res

    async def astart_kernel(self) -> Kernel:
        sid = session_id.get()
        session = await self.session_store.aget(sid)
        try:
            return self.gateway_client.get_kernel(session.kernel_id)
        except KernelNotFoundException:
            logger.debug("kernel not found, creating a new one.")
            env = self._get_kernel_env(session.user_id, session.conv_id)
            request = CreateKernelRequest(env=env)
            res = self.gateway_client.create_kernel(request)
            session.kernel_id = str(res.id)
            await self.session_store.asave(session)
            return res

    @contextmanager
    def upgrade(self, kernel_id: str):
        ws_url = self._get_ws_url(kernel_id)
        logger.debug(f"connecting to {ws_url}")
        try:
            conn = connect(ws_url)
            yield conn
        finally:
            conn.close()

    @asynccontextmanager
    async def aupgrade(self, kernel_id: str):
        ws_url = self._get_ws_url(kernel_id)
        logger.debug(f"connecting to {ws_url}")
        try:
            conn = await aconnect(ws_url)
            yield conn
        finally:
            await conn.close()

    def _get_ws_url(self, kernel_id: str) -> str:
        base = urlparse(str(self.gateway_host))
        ws_scheme = "wss" if base.scheme == "https" else "ws"
        ws_base = urlunparse(base._replace(scheme=ws_scheme))
        return urljoin(ws_base, f"/api/kernels/{kernel_id}/channels")

    def _get_kernel_env(self, userid: str, conv_id: str) -> dict[str, Any]:
        # volume was mounted to `settings.shared_volume` in app
        nfs_path = Path(settings.shared_volume).joinpath(userid).joinpath(conv_id)
        logger.debug(f"creating shared path: {nfs_path}")
        nfs_path.mkdir(exist_ok=True, parents=True)
        env = {
            "KERNEL_USERNAME": userid,
            "KERNEL_VOLUME_MOUNTS": [
                {"name": "shared-vol", "mountPath": settings.shared_volume}
            ],
            "KERNEL_VOLUMES": [
                {
                    "name": "shared-vol",
                    "nfs": {
                        "server": settings.nfs_server,
                        "path": nfs_path.absolute().as_posix(),
                    },
                }
            ],
        }
        if settings.kernel_namespace:
            env["KERNEL_NAMESPACE"] = settings.kernel_namespace
        return env
