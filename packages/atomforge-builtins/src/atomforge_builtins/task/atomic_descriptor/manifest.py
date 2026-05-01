from atomforge_core.registry.task_manifest import TaskManifest

atomic_descriptor_manifest = TaskManifest(
    kind="atomic_descriptor",
    executor_cls=None,
    spec_model="atomforge_builtins.task.atomic_descriptor.spec:AtomicDescriptor",
    result_model="atomforge_builtins.task.atomic_descriptor.result:AtomicDescriptorResult",
    capability_spec="atomforge_builtins.task.atomic_descriptor.definitions:AtomicDescriptorCapabilitySpec",
    environment_factory_cls="atomforge_builtins.task.atomic_descriptor.environment:AtomicDescriptorEnvironmentFactory",
    distribution=["atomforge_builtins"],
)
