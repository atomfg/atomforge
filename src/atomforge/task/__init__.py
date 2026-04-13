from .base import Task

from .singlepoint import SinglePoint, SinglePointExecutor, SinglePointSpec, SinglePointResult

executors = {
    "single_point": SinglePointExecutor()
}