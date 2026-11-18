import numpy as np
import pytest
from ase.build import bulk
from ase.calculators.lj import LennardJones as ASELennardJones
from ase.optimize import BFGS

from atomforge.ase import AtomforgeCalculator
from atomforge_builtins.model.ase_lj import LennardJones


@pytest.fixture
def atoms():
    atoms = bulk("Ar", "fcc", a=5.3, cubic=True) * (2, 1, 1)
    atoms.rattle(0.05, seed=1)
    return atoms


@pytest.fixture
def lj_params():
    return dict(sigma=3.4, epsilon=0.0104, rc=8.0)


def test_matches_ase_lennard_jones(backend, atoms, lj_params):
    reference = atoms.copy()
    reference.calc = ASELennardJones(**lj_params)

    atoms.calc = AtomforgeCalculator(LennardJones(**lj_params), backend=backend)

    assert atoms.get_potential_energy() == pytest.approx(
        reference.get_potential_energy(), rel=1e-10
    )
    np.testing.assert_allclose(
        atoms.get_forces(), reference.get_forces(), rtol=1e-8, atol=1e-12
    )
    assert atoms.calc.last_result.provenance is not None


def test_bfgs_runs(backend, atoms, lj_params):
    atoms.rattle(0.3, seed=2)
    atoms.calc = AtomforgeCalculator(LennardJones(**lj_params), backend=backend)
    initial_energy = atoms.get_potential_energy()

    BFGS(atoms, logfile=None).run(fmax=0.01, steps=50)

    assert atoms.get_potential_energy() < initial_energy
    assert np.abs(atoms.get_forces()).max() < 0.01
