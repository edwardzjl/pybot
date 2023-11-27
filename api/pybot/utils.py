from datetime import datetime, timezone

from pybot.config import settings


def utcnow():
    """
    datetime.datetime.utcnow() does not contain timezone information.
    """
    return datetime.now(timezone.utc)


default_kernel_env = {
    "KERNEL_VOLUME_MOUNTS": [
        {"name": "shared-vol", "mountPath": settings.shared_volume}
    ],
    "KERNEL_VOLUMES": [
        {
            "name": "shared-vol",
            "nfs": {
                "server": settings.nfs_server,
                "path": settings.nfs_path,
            },
        }
    ],
}
if settings.kernel_namespace:
    default_kernel_env["KERNEL_NAMESPACE"] = settings.kernel_namespace
