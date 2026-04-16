import hashlib
import json

from atomforge.model import ModelSpec
from atomforge.task.base.resources import ExecutionResources


def model_session_key(
    model_spec: ModelSpec,
    exec_resources: ExecutionResources,
) -> str:
    """Return a stable hash key for a model spec and execution resource request."""
    payload = {
        "model": model_spec.model_dump(mode="json"),
        "resources": exec_resources.model_dump(mode="json"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
