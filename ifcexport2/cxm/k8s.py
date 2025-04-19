
import os

def in_cluster()->bool:
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return True
    return False

IN_CLUSTER=in_cluster()
if IN_CLUSTER:
    from kubernetes import config
    from kubernetes.config.config_exception import ConfigException
