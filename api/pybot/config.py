from typing import Optional

from pydantic import BaseModel, HttpUrl, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMServiceSettings(BaseModel):
    url: HttpUrl = "http://localhost:8080"
    """llm service url"""
    creds: str = "EMPTY"
    model: str = "cognitivecomputations/dolphincoder-starcoder2-15b"
    eos_token: str = "<|im_end|>"


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

    llm: LLMServiceSettings = LLMServiceSettings()
    jupyter: JupyterSettings = JupyterSettings()
    redis_om_url: RedisDsn = "redis://localhost:6379"
    user_id_header: str = "X-Forwarded-User"
    log_level: str = "INFO"


settings = Settings()
