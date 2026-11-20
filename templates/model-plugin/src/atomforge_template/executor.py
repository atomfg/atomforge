from atomforge_core.model.executor import ModelExecutor
from atomforge_core.model.result import ModelResult
from atomforge_core.property import Property
from atomforge_core.resources.resource_models import ResolvedResources
from atomforge_core.structure import StructureData

from atomforge_template.resources import torch_device, torch_dtype
from atomforge_template.spec import TorchLJ


class TorchLJExecutor(ModelExecutor[TorchLJ]):
    """Runs the model. Constructed once per worker and reused for many structures.

    This is the only module that imports the model's dependencies, and it does so
    inside methods: the host imports this module to check the manifest, but torch
    exists only in the worker environment.

    Do expensive setup (loading weights, compiling) in __init__, not in compute().
    """

    def __init__(self, spec: TorchLJ, resolved_resources: ResolvedResources) -> None:
        super().__init__(spec, resolved_resources)
        import torch

        self._torch = torch
        self.device = torch.device(torch_device(resolved_resources))
        self.dtype = getattr(torch, torch_dtype(resolved_resources))

    def compute(
        self, structure: StructureData, properties: frozenset[Property]
    ) -> ModelResult:
        torch = self._torch

        if any(structure.pbc):
            # A real model would handle periodic systems (and could then declare
            # Property.STRESS, computed from the derivative with respect to strain).
            raise NotImplementedError("torch-lj supports only non-periodic systems.")

        want_forces = Property.FORCES in properties
        positions = torch.tensor(
            structure.positions,
            dtype=self.dtype,
            device=self.device,
            requires_grad=want_forces,
        )

        energy = self._energy(positions)

        forces = None
        if want_forces:
            import numpy as np

            (gradient,) = torch.autograd.grad(energy, positions)
            # ModelResult holds a float64 numpy array whatever dtype the model
            # ran in. astype copies, so the result does not share memory with
            # torch.
            forces = (-gradient).detach().cpu().numpy().astype(np.float64)

        return ModelResult(
            energy=float(energy.detach().cpu()),
            forces=forces,
        )

    def _energy(self, positions):
        torch = self._torch
        n = positions.shape[0]
        i, j = torch.triu_indices(n, n, offset=1, device=self.device)
        r = torch.linalg.vector_norm(positions[i] - positions[j], dim=-1)
        sr6 = (self.spec.sigma / r) ** 6
        return (4.0 * self.spec.epsilon * (sr6**2 - sr6)).sum()
