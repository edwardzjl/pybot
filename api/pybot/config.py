from typing import Optional

from pydantic import BaseModel, HttpUrl, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class JupyterSettings(BaseModel):
    gateway_url: HttpUrl = "http://localhost:8888"
    """URL of the Jupyter Enterprise Gateway."""
    kernel_namespace: Optional[str] = None
    """Namespace to start the kernel in. If not set, a new namespace will be created in form of `${KERNEL_USERNAME}-${UUID}.`"""
    shared_volume_mount_path: str = "/mnt/shared"
    """Path to mount the shared volume in the kernel container."""
    shared_volume_nfs_server: str = "localhost"
    """NFS server to mount the shared volume from."""
    shared_volume_nfs_path: str = "/data/pybot/shared"
    """Path to the shared volume on the NFS server."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    log_level: str = "INFO"
    redis_om_url: RedisDsn = "redis://localhost:6379"
    inference_server_url: HttpUrl = "http://localhost:8080"
    jupyter: JupyterSettings = JupyterSettings()
    user_id_header: str = "X-Forwarded-User"


settings = Settings()
