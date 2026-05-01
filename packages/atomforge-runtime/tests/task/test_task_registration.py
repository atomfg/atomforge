from atomforge_runtime.registry.task.task_registration import TaskRegistration
from runtime_fakes import build_broken_task_registration


def test_task_registration_without_default_executor_validates_strict():
    registration = build_broken_task_registration(executor_class_path=None)

    registration.validate_strict()
    assert isinstance(registration, TaskRegistration)
