from atomforge_core.registry.task_manifest import TaskManifest

analyze_symmetry_manifest = TaskManifest(
    kind="analyze_symmetry",
    executor_cls="atomforge_builtins.task.analyze_symmetry.executor:AnalyzeSymmetryExecutor",
    spec_model="atomforge_builtins.task.analyze_symmetry.spec:AnalyzeSymmetry",
    result_model="atomforge_builtins.task.analyze_symmetry.result:AnalyzeSymmetryResult",
    capability_spec="atomforge_builtins.task.analyze_symmetry.definitions:AnalyzeSymmetryCapabilitySpec",
    environment_factory_cls="atomforge_builtins.task.analyze_symmetry.environment:AnalyzeSymmetryEnvironmentFactory",
    distribution=["atomforge_builtins"],
)
