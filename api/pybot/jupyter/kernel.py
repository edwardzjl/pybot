from pybot.context import session_id
from pybot.jupyter import GatewayClient
from pybot.jupyter.schema import CreateKernelRequest, Kernel, KernelNotFoundException
from pybot.session import RedisSessionStore
from pybot.utils import default_kernel_env


class ContextAwareKernelManager:
    def __init__(self, gateway_url):
        self.gateway_client = GatewayClient(host=gateway_url)
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
