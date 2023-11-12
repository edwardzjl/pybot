from pydantic import AnyHttpUrl, RedisDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    redis_om_url: RedisDsn = "redis://localhost:6379"
    inference_server_url: AnyHttpUrl = "http://localhost:8080"
    shared_volume: str = "/mnt/shared"
    """Volume to share data files with jypyter kernels."""
    user_id_header: str = "kubeflow-userid"


settings = Settings()
