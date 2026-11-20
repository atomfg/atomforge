"""Acceptance tests for the Trivial model, which replaces NoDep ("Model
results as float64 arrays, design" in the engineering log)."""

import numpy as np
import pytest

from atomforge_builtins.model.trivial_model import Trivial, TrivialExecutor
from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_runtime.registry.model.model_registry import ModelRegistry


@pytest.fixture
def trivial_result(example_structure):
    executor = TrivialExecutor(
        spec=Trivial(),
        resolved_resources=ResolvedResources(
            accelerator="cpu", precision=None, messages={}
        ),
    )
    return executor.compute(
        example_structure, frozenset({Property.ENERGY, Property.FORCES})
    )


def test_trivial_kind():
    assert Trivial().kind == "trivial"


def test_trivial_is_registered():
    registration = ModelRegistry.default().get("trivial")
    assert registration.model_spec is Trivial


def test_no_dep_is_no_longer_registered():
    with pytest.raises(KeyError):
        ModelRegistry.default().get("no-dep")


def test_trivial_is_exported_from_builtins_models():
    from atomforge_builtins import model

    assert model.Trivial is Trivial


def test_trivial_environment_requires_numpy():
    from atomforge_builtins.model.trivial_model import (
        TrivialEnvironmentFactory,
    )

    environment = TrivialEnvironmentFactory().build(Trivial())
    assert [r.split("=")[0].split(">")[0] for r in environment.requirements] == [
        "numpy"
    ]


def test_trivial_energy_is_a_float(trivial_result):
    assert type(trivial_result.energy) is float


def test_trivial_forces_are_a_float64_array(trivial_result, example_structure):
    forces = trivial_result.forces
    assert (type(forces), forces.dtype, forces.shape) == (
        np.ndarray,
        np.float64,
        (len(example_structure.numbers), 3),
    )
