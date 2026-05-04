from pydantic import BaseModel, ConfigDict
from typing import Any, TypeVar

from atomforge_core.provenance import Provenance


class TaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provenance: Provenance | None = None

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if self.provenance is None:
            data.pop("provenance", None)
        return data


TaskResultT = TypeVar("TaskResultT", bound=TaskResult)
