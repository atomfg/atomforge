from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, Any

import numpy as np
from ase.calculators.calculator import (
    CalculationFailed,
    Calculator,
    all_changes,
)
from atomforge_builtins.task.single_point import SinglePoint
from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.structure import StructureData
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.registry.task.task_registry import TaskRegistry
from atomforge_runtime.task.resolution import resolve_host_execution

from atomforge.ase._conversion import CHARGE_KEY, SPIN_KEY, atoms_to_structure
from atomforge.backend.subprocess.backend import SubprocessBackend

if TYPE_CHECKING:
    from ase import Atoms
    from atomforge_builtins.task.single_point import SinglePointResult
    from atomforge_core.model.spec import ModelSpec

_PROPERTIES = frozenset({Property.ENERGY, Property.FORCES})


class AtomforgeCalculator(Calculator):
    """ASE calculator that evaluates an atomforge model in an isolated worker.

    Each calculation runs a ``SinglePoint`` task through a backend. Energy and
    forces are always computed together in one request.

    Args:
        model: The ``ModelSpec`` to evaluate. It is fixed for the lifetime of
            the calculator; create a new calculator to use another model.
        backend: Backend to run calculations on. If ``None`` (the default),
            the calculator creates its own ``SubprocessBackend`` on the first
            calculation and shuts it down when the calculator is closed,
            garbage-collected or the interpreter exits. A backend that is
            passed in is never shut down by the calculator.
        exec_resources: Execution resources requested for the model.
        timeout: Per-calculation timeout in seconds. ``None`` uses the backend
            settings.

    Total charge and spin multiplicity are read from ``atoms.info["charge"]``
    and ``atoms.info["spin"]``.

    !!! warning "Reuse calculators"
        A calculator that owns its backend starts a worker and loads the model
        on its first calculation. Creating a new calculator per structure
        therefore pays that start-up cost every time. Attach one calculator to
        many structures, or share a backend between calculators:

        ```python
        with SubprocessBackend() as backend:
            for atoms in structures:
                atoms.calc = AtomforgeCalculator(model, backend=backend)
                atoms.get_potential_energy()
        ```
    """

    implemented_properties = ["energy", "free_energy", "forces"]
    name = "atomforge"

    def __init__(
        self,
        model: ModelSpec,
        *,
        backend: SubprocessBackend | None = None,
        exec_resources: ExecutionResources | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        _check_model_compatibility(model)
        self._model = model
        self._exec_resources = exec_resources
        self._timeout = timeout
        self._backend = backend
        self._owns_backend = backend is None
        self._finalizer: weakref.finalize | None = None
        self.last_result: SinglePointResult | None = None

    @property
    def model(self) -> ModelSpec:
        return self._model

    @property
    def backend(self) -> SubprocessBackend | None:
        """The backend in use, or ``None`` if an owned one has not started."""
        return self._backend

    def _get_backend(self) -> SubprocessBackend:
        if self._backend is None:
            backend = SubprocessBackend()
            # Must not reference self, or the calculator could never be collected.
            self._finalizer = weakref.finalize(self, backend.shutdown)
            self._backend = backend
        return self._backend

    def close(self) -> None:
        """Shut down the backend if this calculator owns it.

        A later calculation starts a new backend.
        """
        if self._owns_backend and self._finalizer is not None:
            self._finalizer()
            self._finalizer = None
            self._backend = None

    def __enter__(self) -> AtomforgeCalculator:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def check_state(self, atoms: Atoms, tol: float = 1e-15) -> list[str]:
        system_changes = super().check_state(atoms, tol=tol)
        if self.atoms is not None:
            for key in (CHARGE_KEY, SPIN_KEY):
                if self.atoms.info.get(key) != atoms.info.get(key):
                    system_changes.append(key)
        return system_changes

    def calculate(
        self,
        atoms: Atoms | None = None,
        properties: list[str] | None = None,
        system_changes: list[str] = all_changes,
    ) -> None:
        super().calculate(atoms, properties, system_changes)
        task = SinglePoint(
            structure=atoms_to_structure(self.atoms), properties=_PROPERTIES
        )
        try:
            result = self._get_backend().execute(
                task,
                self._model,
                exec_resources=self._exec_resources,
                timeout=self._timeout,
            )
        except (ValueError, RuntimeError) as exc:
            raise CalculationFailed(
                f"atomforge calculation with model '{self._model.kind}' failed: {exc}"
            ) from exc

        self.last_result = result
        self.results["energy"] = result.energy
        self.results["free_energy"] = result.energy
        self.results["forces"] = np.asarray(result.forces, dtype=float)

    # Pickling keeps the model and settings but not the backend: worker pipes
    # cannot be pickled. The unpickled calculator starts its own backend lazily.
    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_backend"] = None
        state["_owns_backend"] = True
        state["_finalizer"] = None
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(model={self._model!r})"


def _check_model_compatibility(model: ModelSpec) -> None:
    """Fail early, on the host, if the model cannot provide energy and forces."""
    probe = SinglePoint(
        structure=StructureData(
            positions=[[0.0, 0.0, 0.0]],
            cell=[[0.0, 0.0, 0.0]] * 3,
            numbers=[1],
            pbc=[False, False, False],
        ),
        properties=_PROPERTIES,
    )
    task_registration = TaskRegistry.default().get(probe.kind)
    model_registration = ModelRegistry.default().get(model.kind)
    report = resolve_host_execution(probe, task_registration, model_registration)
    if not report.ok:
        raise ValueError(
            f"Model '{model.kind}' cannot be used with AtomforgeCalculator: "
            f"{report.reason}"
        )
