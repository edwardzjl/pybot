from typing import Optional

from pydantic import HttpUrl, RedisDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    redis_om_url: RedisDsn = "redis://localhost:6379"
    inference_server_url: HttpUrl = "http://localhost:8080"
    jupyter_enterprise_gateway_url: HttpUrl = "http://localhost:8888"
    kernel_namespace: Optional[str] = None
    shared_volume: str = "/mnt/shared"
    """Volume to share data files with jypyter kernels."""
    nfs_server: str = "localhost"
    nfs_path: str = "/data/pybot/shared"
    user_id_header: str = "X-Forwarded-User"


settings = Settings()
