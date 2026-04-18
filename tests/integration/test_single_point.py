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
    from atomforge.task.base.resources import ExecutionResources

    resources = ExecutionResources(accelerator="mps", precision="f64")
    model = LennardJones()
    task = make_task()

    with SubprocessBackend() as backend:
        result = backend.execute(task, model, resources)

    assert result.kind == "single_point"
    assert result.forces is not None
