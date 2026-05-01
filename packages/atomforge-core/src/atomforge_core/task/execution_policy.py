from enum import Enum


class ExecutionPolicy(str, Enum):
    DEFAULT = "default"
    PREFER_MODEL_OVERRIDE = "prefer_model_override"
    REQUIRE_MODEL_OVERRIDE = "require_model_override"
