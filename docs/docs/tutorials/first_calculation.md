# Tutorial: First Calculation


[Download notebook](first_calculation.ipynb)

``` python
from atomforge.backend.subprocess.backend import SubprocessBackend
from atomforge_builtins.task.single_point import SinglePoint
from atomforge_core.structure import StructureData
from atomforge_builtins.model.ase_lj import LennardJones
```

This tutorial shows how a single-point calculation can be done using
`atomforge`.

We start by creating an instance of `StructureData`,

``` python
positions = [[0, 0, 0], [1, 0, 0]]

cell = [[5, 0, 0], 
    [0, 5, 0], 
    [0, 0, 5]]

pbc = [False, False, False]
numbers = [1, 1]

structure = StructureData(positions=positions, numbers=numbers, cell=cell, pbc=pbc)
```

Then we can setup the `TaskSpec`, `ModelSpec` and execute the
computation using the `SubprocessBackend`.

``` python
task = SinglePoint(structure=structure, properties=["energy", "forces"])
model = LennardJones()

with SubprocessBackend() as backend:
    result = backend.execute(task, model)

print(f"{result.kind = }")
print(f"{result.energy = }")
print(f"{result.forces = }")
```

    result.kind = 'single_point'
    result.energy = 0.0054794417442387755
    result.forces = [[-24.0, 0.0, 0.0], [24.0, 0.0, 0.0]]
