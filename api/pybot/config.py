from pydantic import HttpUrl, RedisDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    redis_om_url: RedisDsn = "redis://localhost:6379"
    inference_server_url: HttpUrl = "http://localhost:8080"
    jupyter_enterprise_gateway_url: HttpUrl = "http://localhost:8888"
    shared_volume: str = "/mnt/shared"
    """Volume to share data files with jypyter kernels."""
    user_id_header: str = "kubeflow-userid"


settings = Settings()
