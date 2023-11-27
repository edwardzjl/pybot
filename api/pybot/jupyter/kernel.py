from contextlib import asynccontextmanager, contextmanager
from urllib.parse import urljoin, urlparse, urlunparse

from websockets.client import connect as aconnect
from websockets.sync.client import connect

from pybot.context import session_id
from pybot.jupyter import GatewayClient
from pybot.jupyter.schema import CreateKernelRequest, Kernel, KernelNotFoundException
from pybot.session import RedisSessionStore
from pybot.utils import default_kernel_env


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
            env = {
                "KERNEL_USERNAME": session.user_id,
            }
            request = CreateKernelRequest(env=default_kernel_env | env)
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
            env = {
                "KERNEL_USERNAME": session.user_id,
            }
            request = CreateKernelRequest(env=default_kernel_env | env)
            res = self.gateway_client.create_kernel(request)
            session.kernel_id = str(res.id)
            await self.session_store.asave(session)
            return res

    @contextmanager
    def upgrade(self, kernel_id: str):
        ws_url = self._get_ws_url(kernel_id)
        try:
            conn = connect(ws_url)
            yield conn
        finally:
            conn.close()

    @asynccontextmanager
    async def aupgrade(self, kernel_id: str):
        ws_url = self._get_ws_url(kernel_id)
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
