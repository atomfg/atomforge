"""Unit tests for AtomforgeCalculator using a fake backend (no workers)."""

import pickle

import numpy as np
import pytest
from ase import Atoms
from ase.calculators.calculator import CalculationFailed

from atomforge.ase import AtomforgeCalculator, atoms_to_structure
from atomforge_builtins.model.ase_lj import LennardJones
from atomforge_builtins.task.single_point import SinglePointResult


class FakeBackend:
    def __init__(self, error: Exception | None = None):
        self.tasks = []
        self.shutdown_calls = 0
        self.error = error

    def execute(self, task, model, exec_resources=None, timeout=None):
        if self.error is not None:
            raise self.error
        self.tasks.append(task)
        n = len(task.structure.numbers)
        return SinglePointResult(
            energy=float(len(self.tasks)),
            forces=[[0.1, 0.2, 0.3]] * n,
            stress=None,
            magmoms=None,
            energies=None,
        )

    def shutdown(self):
        self.shutdown_calls += 1


@pytest.fixture
def atoms():
    return Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.74]], cell=[5, 5, 5], pbc=True)


def test_atoms_to_structure(atoms):
    atoms.info.update(charge=1, spin=2)
    structure = atoms_to_structure(atoms)
    assert structure.numbers == [1, 1]
    assert structure.positions[1] == pytest.approx([0, 0, 0.74])
    assert structure.cell == [[5, 0, 0], [0, 5, 0], [0, 0, 5]]
    assert structure.pbc == [True, True, True]
    assert structure.charge == 1
    assert structure.spin_multiplicity == 2


def test_atoms_to_structure_without_charge_or_spin(atoms):
    structure = atoms_to_structure(atoms)
    assert structure.charge is None
    assert structure.spin_multiplicity is None


def test_energy_and_forces_requested_together(atoms):
    backend = FakeBackend()
    atoms.calc = AtomforgeCalculator(LennardJones(), backend=backend)

    energy = atoms.get_potential_energy()
    forces = atoms.get_forces()

    assert len(backend.tasks) == 1
    assert {p.value for p in backend.tasks[0].properties} == {"energy", "forces"}
    assert energy == 1.0
    assert atoms.get_potential_energy(force_consistent=True) == 1.0
    assert isinstance(forces, np.ndarray)
    assert forces.shape == (2, 3)
    assert atoms.calc.last_result is not None


def test_results_cached_until_positions_change(atoms):
    backend = FakeBackend()
    atoms.calc = AtomforgeCalculator(LennardJones(), backend=backend)

    atoms.get_potential_energy()
    atoms.get_potential_energy()
    assert len(backend.tasks) == 1

    atoms.positions[1, 2] += 0.1
    assert atoms.get_potential_energy() == 2.0
    assert len(backend.tasks) == 2


@pytest.mark.parametrize("key", ["charge", "spin"])
def test_charge_or_spin_change_triggers_recalculation(atoms, key):
    backend = FakeBackend()
    atoms.calc = AtomforgeCalculator(LennardJones(), backend=backend)

    atoms.get_potential_energy()
    atoms.info[key] = 1
    atoms.get_potential_energy()

    assert len(backend.tasks) == 2
    structure = backend.tasks[-1].structure
    value = structure.charge if key == "charge" else structure.spin_multiplicity
    assert value == 1


def test_backend_errors_raise_calculation_failed(atoms):
    backend = FakeBackend(error=RuntimeError("worker crashed"))
    atoms.calc = AtomforgeCalculator(LennardJones(), backend=backend)
    with pytest.raises(CalculationFailed, match="worker crashed"):
        atoms.get_potential_energy()


def test_given_backend_is_not_shut_down(atoms):
    backend = FakeBackend()
    with AtomforgeCalculator(LennardJones(), backend=backend) as calc:
        atoms.calc = calc
        atoms.get_potential_energy()
    calc.close()
    assert backend.shutdown_calls == 0
    assert calc.backend is backend


def test_owned_backend_is_lazy_and_closed(atoms, mocker):
    backend = FakeBackend()
    factory = mocker.patch(
        "atomforge.ase._calculator.SubprocessBackend", return_value=backend
    )
    calc = AtomforgeCalculator(LennardJones())
    assert calc.backend is None
    factory.assert_not_called()

    atoms.calc = calc
    atoms.get_potential_energy()
    factory.assert_called_once()

    calc.close()
    calc.close()
    assert backend.shutdown_calls == 1
    assert calc.backend is None


def test_owned_backend_shut_down_on_garbage_collection(atoms, mocker):
    backend = FakeBackend()
    mocker.patch("atomforge.ase._calculator.SubprocessBackend", return_value=backend)
    calc = AtomforgeCalculator(LennardJones())
    calc.get_potential_energy(atoms)

    del calc
    import gc

    gc.collect()
    assert backend.shutdown_calls == 1


def test_pickle_drops_backend(atoms):
    backend = FakeBackend()
    calc = AtomforgeCalculator(LennardJones(sigma=2.0), backend=backend)
    calc.get_potential_energy(atoms)

    restored = pickle.loads(pickle.dumps(calc))

    assert restored.model == LennardJones(sigma=2.0)
    assert restored.backend is None
    restored.close()  # must not touch the original backend
    assert backend.shutdown_calls == 0


def test_unregistered_model_rejected():
    from atomforge_core.model.spec import ModelSpec

    class Unregistered(ModelSpec):
        kind: str = "not-a-registered-model"

    with pytest.raises(Exception):
        AtomforgeCalculator(Unregistered())
