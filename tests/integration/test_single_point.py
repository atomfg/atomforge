from atomforge.backend.subprocess.backend import SubprocessBackend
from atomforge.model.ase_lj import LennardJones


def make_task():
    from ase import Atoms
    from atomforge.structure import Structure
    from atomforge.task.singlepoint import SinglePoint

    atoms = Atoms(
        "HOH", positions=[[0, 0, 0], [0, 0, 1], [1, 0, 0]], cell=[10, 10, 10], pbc=False
    )

    structure = Structure.from_ase(atoms)
    task = SinglePoint(structure=structure, properties=["forces"])

    return task


def test_single_point():
    from atomforge.task.core.resources import ExecutionResources
    from atomforge.registry.task.registry import TaskRegistry
    from atomforge.model.registry.builtin import get_default_model_registry

    resources = ExecutionResources(accelerator="cpu", precision="f64")
    model = LennardJones()
    task = make_task()

    task_registry = TaskRegistry.default()  # Ensure the registry is loaded
    registration = task_registry.get(task.kind)
    task_env_spec = registration.environment_factory(task)


    model_registry = get_default_model_registry()
    model_registration = model_registry.get(model.kind)
    model_env_spec = model_registration.environment_factory(model)

    print("Task environment spec:", task_env_spec)
    print("Model environment spec:", model_env_spec)

    print(task_env_spec + model_env_spec)







    with SubprocessBackend() as backend:
        result = backend.execute(task, model, resources)

    assert result.kind == "single_point"
    assert result.forces is not None
