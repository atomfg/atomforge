from pydantic import BaseModel, ConfigDict


class TaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
