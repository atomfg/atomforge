from pydantic import BaseModel, ConfigDict


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
