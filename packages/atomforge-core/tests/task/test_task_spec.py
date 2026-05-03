from atomforge_core.property import Property
from atomforge_core.task.spec import TaskSpec


class ExampleTask(TaskSpec):
    kind: str = "example-task"

    def required_model_properties(self) -> frozenset[Property]:
        return frozenset()


def test_task_spec_requires_model_defaults_true():
    assert ExampleTask.requires_model is True
