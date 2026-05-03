from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.task.executability import HostExecutabilityReport
from atomforge_core.task.executor import TaskExecutionContext
from atomforge_core.task.execution_policy import ExecutionPolicy
from atomforge_runtime.task.host_checks import check_host_executability, check_required_properties
from atomforge_runtime.task.resolution import resolve_worker_execution
from runtime_fakes import (
    FakeModel,
    FakeModelExecutor,
    FakeTask,
    FakeTaskOnly,
    build_broken_model_registration,
    build_broken_task_registration,
    build_model_registration,
    build_task_registration,
    build_task_only_registration,
)


def build_model_executor(scale: float = 1.0) -> FakeModelExecutor:
    return FakeModelExecutor(
        spec=FakeModel(scale=scale),
        resolved_resources=ResolvedResources(
            accelerator="cpu",
            precision=None,
            messages={},
        ),
    )


def test_host_executability_supported_properties_and_route(example_structure):
    task_spec = FakeTask(structure=example_structure)
    report = check_host_executability(
        task_spec,
        build_task_registration(),
        build_model_registration(),
    )

    assert report.ok is True
    assert report.selected_route is not None
    assert report.candidate_routes


def test_check_required_properties_success_returns_ok_report(example_structure):
    report = check_required_properties(
        FakeTask(structure=example_structure),
        build_model_registration(),
    )

    assert isinstance(report, HostExecutabilityReport)
    assert report.ok is True
    assert report.reason is None
    assert report.selected_route is None
    assert report.candidate_routes == ()


def test_host_executability_missing_properties(example_structure):
    model_registration = build_broken_model_registration(
        supported_properties_path=SymbolPath("runtime_fakes:EmptySupportedProperties")
    )
    report = check_host_executability(
        FakeTask(structure=example_structure),
        build_task_registration(),
        model_registration,
    )

    assert report.ok is False
    assert report.reason is not None
    assert report.selected_route is None
    assert report.candidate_routes == ()


def test_host_executability_no_policy_allowed_route(example_structure):
    task_registration = build_broken_task_registration(executor_class_path=None)
    model_registration = build_broken_model_registration(task_overrides={})
    task_spec = FakeTask(
        structure=example_structure,
        execution_policy=ExecutionPolicy.DEFAULT,
    )

    report = check_host_executability(task_spec, task_registration, model_registration)

    assert report.ok is False
    assert "No policy-allowed executor route" in report.reason
    assert report.selected_route is None
    assert report.candidate_routes == ()


def test_host_executability_override_only_with_matching_override(example_structure):
    task_registration = build_broken_task_registration(executor_class_path=None)
    task_spec = FakeTask(
        structure=example_structure,
        execution_policy=ExecutionPolicy.REQUIRE_MODEL_OVERRIDE,
    )

    report = check_host_executability(
        task_spec,
        task_registration,
        build_model_registration(),
    )

    assert report.ok is True
    assert report.selected_route is not None
    assert report.candidate_routes
    assert report.selected_route.route_kind.value == "model_override"


def test_host_executability_override_only_without_override(example_structure):
    task_registration = build_broken_task_registration(executor_class_path=None)
    model_registration = build_broken_model_registration(task_overrides={})
    task_spec = FakeTask(
        structure=example_structure,
        execution_policy=ExecutionPolicy.REQUIRE_MODEL_OVERRIDE,
    )

    report = check_host_executability(task_spec, task_registration, model_registration)

    assert report.ok is False
    assert report.selected_route is None
    assert report.candidate_routes == ()


def test_resolve_worker_execution_default_route(example_structure):
    task_spec = FakeTask(
        structure=example_structure,
        execution_policy=ExecutionPolicy.DEFAULT,
    )
    route, executor_cls, compatibility = resolve_worker_execution(
        task_spec,
        build_task_registration(),
        build_model_registration(),
        TaskExecutionContext(model_executor=build_model_executor()),
    )

    assert route.route_kind.value == "default_executor"
    assert executor_cls.__name__ == "FakeTaskExecutor"
    assert compatibility.ok is True


def test_resolve_worker_execution_prefer_override_uses_override(example_structure):
    task_spec = FakeTask(
        structure=example_structure,
        execution_policy=ExecutionPolicy.PREFER_MODEL_OVERRIDE,
    )
    route, executor_cls, compatibility = resolve_worker_execution(
        task_spec,
        build_task_registration(),
        build_model_registration(),
        TaskExecutionContext(model_executor=build_model_executor()),
    )

    assert route.route_kind.value == "model_override"
    assert executor_cls.__name__ == "FakeOverrideTaskExecutor"
    assert compatibility.ok is True


def test_resolve_worker_execution_prefer_override_falls_back_to_default(example_structure):
    task_spec = FakeTask(
        structure=example_structure,
        execution_policy=ExecutionPolicy.PREFER_MODEL_OVERRIDE,
        minimum_override_scale=2.0,
    )
    route, executor_cls, compatibility = resolve_worker_execution(
        task_spec,
        build_task_registration(),
        build_model_registration(),
        TaskExecutionContext(model_executor=build_model_executor(scale=1.0)),
    )

    assert route.route_kind.value == "default_executor"
    assert executor_cls.__name__ == "FakeTaskExecutor"
    assert compatibility.ok is True


def test_resolve_worker_execution_require_override_incompatible_returns_incompatibility(
    example_structure,
):
    task_spec = FakeTask(
        structure=example_structure,
        execution_policy=ExecutionPolicy.REQUIRE_MODEL_OVERRIDE,
        minimum_override_scale=2.0,
    )

    route, executor_cls, compatibility = resolve_worker_execution(
        task_spec,
        build_task_registration(),
        build_model_registration(),
        TaskExecutionContext(model_executor=build_model_executor(scale=1.0)),
    )

    assert route.route_kind.value == "model_override"
    assert executor_cls.__name__ == "FakeOverrideTaskExecutor"
    assert compatibility.ok is False
    assert "requires model scale >=" in compatibility.reason


def test_resolve_worker_execution_require_override_without_override_raises(example_structure):
    task_spec = FakeTask(
        structure=example_structure,
        execution_policy=ExecutionPolicy.REQUIRE_MODEL_OVERRIDE,
    )

    try:
        resolve_worker_execution(
            task_spec,
            build_task_registration(),
            build_broken_model_registration(task_overrides={}),
            TaskExecutionContext(model_executor=build_model_executor()),
        )
    except ValueError as exc:
        assert "No policy-allowed executor route" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for missing required override")


def test_model_free_required_properties_success():
    report = check_required_properties(
        FakeTaskOnly(value=3),
        None,
    )

    assert isinstance(report, HostExecutabilityReport)
    assert report.ok is True


def test_model_free_host_executability_uses_default_route():
    task_spec = FakeTaskOnly(value=4)
    report = check_host_executability(
        task_spec,
        build_task_only_registration(),
        None,
    )

    assert report.ok is True
    assert report.selected_route is not None
    assert report.selected_route.route_kind.value == "default_executor"


def test_model_free_require_override_is_rejected():
    task_spec = FakeTaskOnly(
        value=4,
        execution_policy=ExecutionPolicy.REQUIRE_MODEL_OVERRIDE,
    )
    report = check_host_executability(
        task_spec,
        build_task_only_registration(),
        None,
    )

    assert report.ok is False
    assert "model-free" in report.reason


def test_resolve_worker_execution_model_free_route():
    task_spec = FakeTaskOnly(value=5)
    route, executor_cls, compatibility = resolve_worker_execution(
        task_spec,
        build_task_only_registration(),
        None,
        TaskExecutionContext(model_executor=None, resolved_resources=None),
    )

    assert route.route_kind.value == "default_executor"
    assert executor_cls.__name__ == "FakeTaskOnlyExecutor"
    assert compatibility.ok is True


def test_model_backed_task_without_model_fails(example_structure):
    report = check_host_executability(
        FakeTask(structure=example_structure),
        build_task_registration(),
        None,
    )

    assert report.ok is False
    assert "requires a model" in report.reason
